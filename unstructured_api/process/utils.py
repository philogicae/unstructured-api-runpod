import logging
from base64 import b64decode
from os import close, listdir, remove
from pathlib import PurePath
from re import split as re_split
from tempfile import mkstemp
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from imagededup.methods import PHash
from magika import Magika

from unstructured_api.settings import MAX_SIZE, URL_TIMEOUT

logger = logging.getLogger(__name__)

magika = Magika()


def get_filename(
    filename: str | None = None, file_url: str | None = None
) -> str | None:
    if filename:
        return filename
    if file_url:
        return PurePath(urlparse(file_url).path).name or None
    return None


def exceeds_size(data: bytes | str, max_size: int = MAX_SIZE) -> bool:
    if isinstance(data, bytes):
        return len(data) > max_size
    return len(data) > max_size * 4 // 3


def natural_sort(file_list: list[str]) -> list[str]:
    return sorted(
        file_list,
        key=lambda s: [
            int(text) if text.isdigit() else text.lower()
            for text in re_split("([0-9]+)", s)
        ],
    )


def detect_content_type(file_path: str) -> str | None:
    try:
        result = magika.identify_path(file_path)
        if result.ok:
            return result.output.mime_type
    except Exception:
        logger.warning("Failed to detect content type for %s", file_path, exc_info=True)
    return None


def base64_to_tempfile(content: str, suffix: str = "") -> str:
    fd, path = mkstemp(suffix=suffix)
    with open(fd, "wb") as f:
        f.write(b64decode(content))
    return path


def url_to_tempfile(url: str, suffix: str = "") -> str:
    scheme = urlparse(url).scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {scheme or '(none)'}")
    req = Request(url, headers={"User-Agent": "unstructured-api/1.0"})
    fd, path = mkstemp(suffix=suffix)
    try:
        with urlopen(req, timeout=URL_TIMEOUT) as response:
            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    cl = int(content_length)
                except ValueError:
                    cl = 0
                if cl and cl > MAX_SIZE:
                    raise ValueError(f"Download exceeds max size ({MAX_SIZE} bytes)")
            with open(fd, "wb") as f:
                total = 0
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_SIZE:
                        raise ValueError(
                            f"Download exceeds max size ({MAX_SIZE} bytes)"
                        )
                    f.write(chunk)
    except Exception:
        try:
            close(fd)
        except OSError:
            pass
        remove(path)
        raise
    logger.info("Downloaded %s to %s (%d bytes)", url, path, total)
    return path


def find_duplicate_images(image_dir: str) -> set[str]:
    folder = listdir(image_dir)
    if not folder:
        return set()
    phasher = PHash()
    duplicates = phasher.find_duplicates(PurePath(image_dir))
    images_to_remove: set[str] = set()
    for file in natural_sort(folder):
        filepath = f"{image_dir}/{file}"
        if filepath not in images_to_remove:
            for dup in duplicates.get(file, []):
                images_to_remove.add(f"{image_dir}/{dup}")
    if images_to_remove:
        logger.info("Found %d duplicate images", len(images_to_remove))
    return images_to_remove


def cleanup(path: str) -> None:
    try:
        remove(path)
    except OSError:
        pass
