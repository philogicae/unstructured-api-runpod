from os import path, remove
from pathlib import Path
from time import time
from typing import Any

from PIL import Image as PILImage
from unstructured.cleaners.core import clean, replace_unicode_quotes
from unstructured.documents.elements import Element, Text
from unstructured.file_utils.filetype import FileType
from unstructured.partition.auto import _PartitionerLoader, partition  # ty:ignore[unresolved-import]
from unstructured.partition.common import UnsupportedFileFormatError  # ty:ignore[unresolved-import]

from unstructured_api.settings import (
    EXTRACT_IMAGE_BLOCK_TYPES,
    MIN_IMAGE_PIXELS,
    PDF_IMAGE_DPI,
)
from unstructured_api.process.utils import (
    base64_to_tempfile,
    cleanup,
    detect_content_type,
    guess_suffix,
    url_to_tempfile,
)


def partitioner(file: str, output_dir: str) -> list[Element]:
    content_type = detect_content_type(file)
    is_pdf = content_type is not None and "pdf" in content_type
    partitioning_kwargs: dict[str, Any] = {
        "content_type": content_type,
        "strategy": "hi_res",
        "ocr_mode": "individual_blocks",
        "pdf_image_dpi": PDF_IMAGE_DPI,
        "infer_table_structure": False,
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
        return partition(file, **partitioning_kwargs)
    except UnsupportedFileFormatError:
        file_type = FileType.from_mime_type(content_type) if content_type else None  # ty:ignore[unresolved-attribute]
        if file_type is None or not file_type.is_partitionable:
            raise
        partitioner_fn = _PartitionerLoader().get(file_type)
        fallback_kwargs = {
            k: v for k, v in partitioning_kwargs.items() if k != "content_type"
        }
        return partitioner_fn(filename=file, **fallback_kwargs)


def clean_text(text: str) -> str:
    if not text:
        return ""
    from unicodedata import normalize

    return normalize(
        "NFKC",
        replace_unicode_quotes(
            clean(
                text,
                extra_whitespace=True,
                dashes=True,
                bullets=True,
                trailing_punctuation=True,
                lowercase=False,
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
        return False


def filter_elements(elements: list[Element], image_dir: str) -> list[Element]:
    filtered: list[Element] = []
    for element in elements:
        image_path = element.metadata.image_path
        too_small = (
            image_path
            and element.category == "Image"
            and is_image_too_small(image_path)
        )
        if too_small:
            try:
                remove(image_path)
            except OSError:
                pass
            continue
        if element.category == "Table" and element.metadata.text_as_html:
            filtered.append(
                Text(text=element.metadata.text_as_html, metadata=element.metadata)
            )
        else:
            filtered.append(element)
    return filtered


def extract(source: str, images_dir: str) -> list[Element]:
    return filter_elements(
        cleanup_elements(partitioner(source, images_dir)),
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


def parse_document(
    file_content: str | None = None,
    file_url: str | None = None,
    file_path: str | None = None,
    filename: str | None = None,
) -> dict:
    temp_path = None
    num_pages = None
    try:
        if file_path:
            source = file_path
        elif file_content:
            suffix = guess_suffix(filename)
            temp_path = base64_to_tempfile(file_content, suffix)
            source = temp_path
        elif file_url:
            suffix = guess_suffix(filename)
            temp_path = url_to_tempfile(file_url, suffix)
            source = temp_path
        else:
            return {
                "elements": [],
                "metadata": {
                    "error": "No input provided (file_content, file_url, or file_path required)"
                },
                "error": "No input provided",
            }

        started = time()

        images_dir = f"{path.splitext(source)[0]}_images"
        Path(images_dir).mkdir(exist_ok=True)

        elements = extract(source, images_dir)

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

        return {
            "elements": serialized,
            "metadata": {
                "filename": filename or path.basename(source),
                "file_size": file_size,
                "num_elements": len(serialized),
                "num_pages": num_pages,
                "processing_time": round(processing_time, 2),
            },
            "error": None,
        }
    except Exception as e:
        return {
            "elements": [],
            "metadata": {},
            "error": str(e),
        }
    finally:
        if temp_path:
            cleanup(temp_path)
