from __future__ import annotations

import copy
import io
import json
import logging
from os import listdir, path, remove, walk
from pathlib import Path, PurePath
from re import split as re_split
from shutil import rmtree
from time import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from unstructured.documents.elements import Element
from unicodedata import normalize
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image as PILImage

from unstructured_api.process.utils import (
    base64_to_tempfile,
    cleanup,
    detect_content_type,
    url_to_tempfile,
)
from unstructured_api.settings import (
    EXTRACT_IMAGE_BLOCK_TYPES,
    MIN_IMAGE_PIXELS,
    PDF_IMAGE_DPI,
)

logger = logging.getLogger(__name__)


def _natural_sort(file_list: list[str]) -> list[str]:
    return sorted(
        file_list,
        key=lambda s: [
            int(text) if text.isdigit() else text.lower()
            for text in re_split("([0-9]+)", s)
        ],
    )


def find_duplicate_images(image_dir: str) -> set[str]:
    from imagededup.methods import PHash

    folder = listdir(image_dir)
    if not folder:
        return set()
    phasher = PHash()
    duplicates = phasher.find_duplicates(PurePath(image_dir))
    images_to_remove: set[str] = set()
    for file in _natural_sort(folder):
        filepath = f"{image_dir}/{file}"
        if filepath not in images_to_remove:
            for dup in duplicates.get(file, []):
                images_to_remove.add(f"{image_dir}/{dup}")
    if images_to_remove:
        logger.info("Found %d duplicate images", len(images_to_remove))
    return images_to_remove


def partitioner(
    file: str, output_dir: str, filename: str | None = None
) -> list[Element]:
    from unstructured.documents.elements import Text
    from unstructured.file_utils.filetype import FileType
    from unstructured.partition.auto import _PartitionerLoader, partition
    from unstructured.partition.common import UnsupportedFileFormatError

    content_type = detect_content_type(file)
    is_pdf = content_type is not None and "pdf" in content_type
    partitioning_kwargs: dict[str, Any] = {
        "content_type": content_type,
        "strategy": "hi_res",
        "ocr_mode": "individual_blocks",
        "pdf_image_dpi": PDF_IMAGE_DPI,
        "infer_table_structure": False,
        "metadata_filename": filename,
    }
    if is_pdf:
        partitioning_kwargs.update(
            {
                "extract_images_in_pdf": True,
                "extract_image_block_output_dir": output_dir,
                "extract_image_block_types": EXTRACT_IMAGE_BLOCK_TYPES,
            }
        )
    try:
        partitioned = partition(file, **partitioning_kwargs)
    except UnsupportedFileFormatError:
        file_type = FileType.from_mime_type(content_type) if content_type else None
        if file_type is None or not file_type.is_partitionable:
            raise
        partitioner_fn = _PartitionerLoader().get(file_type)
        fallback_kwargs = {
            k: v for k, v in partitioning_kwargs.items() if k != "content_type"
        }
        partitioned = partitioner_fn(filename=file, **fallback_kwargs)
    for i, element in enumerate(partitioned):
        if (
            element.category in ["Image", "Table"]
            and not element.metadata.image_path
            and element.metadata.text_as_html
        ):
            partitioned[i] = Text(
                text=element.metadata.text_as_html,
                metadata=element.metadata,
            )
    return partitioned


def clean_text(text: str) -> str:
    from unstructured.cleaners.core import clean, replace_unicode_quotes

    if not text:
        return ""
    return normalize(
        "NFKC",
        replace_unicode_quotes(
            clean(
                text,
                extra_whitespace=True,
                dashes=True,
                bullets=True,
                trailing_punctuation=True,
                lowercase=True,
            )
        ),
    )


def cleanup_elements(elements: list[Element]) -> list[Element]:
    for element in elements:
        element.apply(clean_text)  # ty:ignore[unresolved-attribute]
    return elements


def is_image_too_small(image_path: str) -> bool:
    try:
        with PILImage.open(image_path) as img:
            return img.width * img.height < MIN_IMAGE_PIXELS
    except Exception:
        logger.warning("Failed to open image %s", image_path, exc_info=True)
        return False


def filter_elements(elements: list[Element], image_dir: str) -> list[Element]:
    from unstructured.documents.elements import Image, Text

    filtered: list[Element] = []
    duplicated_images = find_duplicate_images(image_dir)
    small_removed = 0
    for element in elements:
        image_path = element.metadata.image_path
        duplicated = image_path in duplicated_images
        too_small = (
            image_path
            and not duplicated
            and element.category == "Image"
            and is_image_too_small(image_path)
        )
        if not duplicated and not too_small:
            if element.category == "Table":
                filtered.append(
                    Image(
                        text=element.text,
                        metadata=element.metadata,
                    )
                )
            else:
                filtered.append(element)
        elif image_path:
            try:
                remove(image_path)
            except OSError:
                pass
            if too_small:
                small_removed += 1
            elif duplicated and element.category == "Table":
                if element.metadata.text_as_html:
                    filtered.append(
                        Text(
                            text=element.metadata.text_as_html,
                            metadata=element.metadata,
                        )
                    )
                else:
                    filtered.append(element)
    if small_removed:
        logger.info("Removed %d small icon image(s)", small_removed)
    return filtered


def extract(source: str, images_dir: str, filename: str | None = None) -> list[Element]:
    return filter_elements(
        cleanup_elements(partitioner(source, images_dir, filename)),
        images_dir,
    )


def serialize_element(element: Element) -> dict:
    meta = element.metadata
    return {
        "type": element.category,
        "text": element.text,
        "metadata": {
            "page_number": meta.page_number,
            "filename": meta.filename,
            "filetype": meta.filetype,
            "image_path": str(meta.image_path) if meta.image_path else None,
            "image_base64": meta.image_base64,
            "text_as_html": meta.text_as_html,
            "link_urls": meta.link_urls,
            "link_texts": meta.link_texts,
            "languages": meta.languages,
            "is_continuation": meta.is_continuation,
        },
    }


def serialize_elements(elements: list[Element]) -> list[dict]:
    return [serialize_element(e) for e in elements]


def _create_result_zip(
    serialized: list[dict],
    metadata: dict,
    images_dir: str,
) -> bytes:
    serialized = copy.deepcopy(serialized)
    for el in serialized:
        img_path = el["metadata"]["image_path"]
        if img_path:
            el["metadata"]["image_path"] = f"images/{path.basename(img_path)}"

    elements_json = json.dumps(serialized, ensure_ascii=False, separators=(",", ":"))
    metadata_json = json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))

    buf = io.BytesIO()
    with ZipFile(buf, "w", ZIP_DEFLATED) as zf:
        zf.writestr("elements.json", elements_json)
        zf.writestr("metadata.json", metadata_json)
        if path.exists(images_dir):
            for root, _, files in walk(images_dir):
                for f in files:
                    file_path = path.join(root, f)
                    zf.write(file_path, f"images/{f}")
    return buf.getvalue()


def parse_document(
    file_content: str | None = None,
    file_url: str | None = None,
    file_path: str | None = None,
    filename: str | None = None,
) -> bytes | dict:
    temp_path = None
    num_pages = None
    try:
        if file_path:
            source = file_path
        elif file_content:
            source = base64_to_tempfile(
                file_content, PurePath(filename).suffix if filename else ""
            )
            temp_path = source
        elif file_url:
            source = url_to_tempfile(
                file_url, PurePath(filename).suffix if filename else ""
            )
            temp_path = source
        else:
            return {"error": "No input provided"}

        started = time()

        images_dir = f"{path.splitext(source)[0]}_images"
        Path(images_dir).mkdir(exist_ok=True)

        elements = extract(source, images_dir, filename)

        file_size = path.getsize(source) if path.exists(source) else 0
        serialized = serialize_elements(elements)
        processing_time = time() - started

        if serialized:
            all_pages = {
                e["metadata"]["page_number"]
                for e in serialized
                if e["metadata"]["page_number"]
            }
            if all_pages:
                num_pages = max(all_pages)

        metadata = {
            "filename": filename or path.basename(source),
            "file_size": file_size,
            "num_elements": len(serialized),
            "num_pages": num_pages,
            "processing_time": round(processing_time, 2),
        }

        zip_bytes = _create_result_zip(serialized, metadata, images_dir)

        logger.info(
            "Parsed %s: %d elements, %d pages, %.2fs",
            metadata["filename"],
            len(serialized),
            num_pages or 0,
            processing_time,
        )

        return zip_bytes
    except Exception as e:
        logger.exception("Failed to parse document")
        err_msg = str(e).split("\n")[0]
        if temp_path:
            err_msg = err_msg.replace(temp_path, "<path>")
        return {"error": f"Processing failed: {type(e).__name__}: {err_msg}"}
    finally:
        if temp_path:
            cleanup(temp_path)
        if "images_dir" in locals() and path.exists(images_dir):
            rmtree(images_dir, ignore_errors=True)
