from base64 import b64decode
from os import remove
from pathlib import Path
from tempfile import mkstemp
from urllib.request import urlopen

from magika import Magika

_magika = Magika()


def detect_content_type(file_path: str) -> str | None:
    try:
        result = _magika.identify_path(file_path)
        if result.ok:
            return result.output.mime_type
    except Exception:
        pass
    return None


def base64_to_tempfile(content: str, suffix: str = "") -> str:
    fd, path = mkstemp(suffix=suffix)
    with open(fd, "wb") as f:
        f.write(b64decode(content))
    return path


def url_to_tempfile(url: str, suffix: str = "") -> str:
    fd, path = mkstemp(suffix=suffix)
    with urlopen(url) as response:
        with open(fd, "wb") as f:
            f.write(response.read())
    return path


def cleanup(path: str) -> None:
    try:
        remove(path)
    except OSError:
        pass


def guess_suffix(filename: str | None) -> str:
    if not filename:
        return ""
    return Path(filename).suffix or ""
