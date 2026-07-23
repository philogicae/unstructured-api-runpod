import logging
from base64 import b64decode
from os import close, remove
from tempfile import mkstemp
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from magika import Magika

from unstructured_api.settings import MAX_DOWNLOAD_SIZE, URL_TIMEOUT

logger = logging.getLogger(__name__)

_magika = None


def _get_magika():
    global _magika
    if _magika is None:
        _magika = Magika()
    return _magika


def detect_content_type(file_path: str) -> str | None:
    try:
        result = _get_magika().identify_path(file_path)
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
                if cl and cl > MAX_DOWNLOAD_SIZE:
                    raise ValueError(
                        f"Download exceeds max size ({MAX_DOWNLOAD_SIZE} bytes)"
                    )
            with open(fd, "wb") as f:
                total = 0
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_SIZE:
                        raise ValueError(
                            f"Download exceeds max size ({MAX_DOWNLOAD_SIZE} bytes)"
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


def cleanup(path: str) -> None:
    try:
        remove(path)
    except OSError:
        pass
