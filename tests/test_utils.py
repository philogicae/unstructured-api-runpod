import os
import shutil
import tempfile
from base64 import b64encode
from http.server import HTTPServer, SimpleHTTPRequestHandler
from os import path
from tempfile import NamedTemporaryFile
from threading import Thread
from unittest.mock import patch

import pytest

from unstructured_api.process.utils import (
    base64_to_tempfile,
    cleanup,
    detect_content_type,
    url_to_tempfile,
)
from unstructured_api.settings import MAX_DOWNLOAD_SIZE  # noqa: F401


def test_base64_to_tempfile_roundtrip():
    original = b"hello world test content"
    b64 = b64encode(original).decode("utf-8")
    temp = base64_to_tempfile(b64, suffix=".txt")
    try:
        with open(temp, "rb") as f:
            assert f.read() == original
    finally:
        cleanup(temp)
    assert not path.exists(temp)


def test_base64_to_tempfile_with_suffix():
    b64 = b64encode(b"test").decode("utf-8")
    temp = base64_to_tempfile(b64, suffix=".pdf")
    try:
        assert temp.endswith(".pdf")
    finally:
        cleanup(temp)


def test_cleanup_nonexistent():
    cleanup("/tmp/nonexistent_file_12345")
    assert True


def test_detect_content_type_text():
    with NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"Hello, this is a text file.")
        tmp = f.name
    try:
        ct = detect_content_type(tmp)
        assert ct is not None
        assert "text" in ct
    finally:
        cleanup(tmp)


def test_detect_content_type_nonexistent():
    assert detect_content_type("/nonexistent/path/file.txt") is None


def test_detect_content_type_corrupt_file():
    with NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c")
        tmp = f.name
    try:
        result = detect_content_type(tmp)
        assert result is None or isinstance(result, str)
    finally:
        cleanup(tmp)


def test_detect_content_type_magika_exception():
    with patch("unstructured_api.process.utils._get_magika") as mock_magika:
        mock_magika.return_value.identify_path.side_effect = RuntimeError(
            "magika crashed"
        )
        with NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test content")
            tmp = f.name
        try:
            assert detect_content_type(tmp) is None
        finally:
            cleanup(tmp)


def test_url_to_tempfile_with_local_server():
    handler = SimpleHTTPRequestHandler
    httpd = HTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        test_dir = tempfile.mkdtemp()
        test_file = path.join(test_dir, "test.txt")
        with open(test_file, "wb") as f:
            f.write(b"url download test")

        cwd = os.getcwd()
        os.chdir(test_dir)
        try:
            temp = url_to_tempfile(f"http://127.0.0.1:{port}/test.txt", suffix=".txt")
            try:
                with open(temp, "rb") as f:
                    assert f.read() == b"url download test"
            finally:
                cleanup(temp)
        finally:
            os.chdir(cwd)
            shutil.rmtree(test_dir)
    finally:
        httpd.shutdown()


def test_url_to_tempfile_rejects_file_scheme():

    with pytest.raises(ValueError, match="Unsupported URL scheme"):
        url_to_tempfile("file:///etc/passwd", suffix=".txt")


def test_url_to_tempfile_content_length_too_large():

    class BigFileHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            body = b"x" * 1024
            self.send_response(200)
            self.send_header("Content-Length", str(999 * 1024 * 1024))
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            pass

    httpd = HTTPServer(("127.0.0.1", 0), BigFileHandler)
    port = httpd.server_address[1]
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(ValueError, match="exceeds max size"):
            url_to_tempfile(f"http://127.0.0.1:{port}/big.txt", suffix=".txt")
    finally:
        httpd.shutdown()


def test_url_to_tempfile_streaming_too_large():

    with patch("unstructured_api.process.utils.MAX_DOWNLOAD_SIZE", 1024 * 1024):
        chunk_size = 64 * 1024
        chunks_needed = (1024 * 1024 // chunk_size) + 2

        class StreamingBigHandler(SimpleHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.end_headers()
                for _ in range(chunks_needed):
                    self.wfile.write(b"x" * chunk_size)

            def log_message(self, format: str, *args: object) -> None:
                pass

        httpd = HTTPServer(("127.0.0.1", 0), StreamingBigHandler)
        port = httpd.server_address[1]
        thread = Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            with pytest.raises(ValueError, match="exceeds max size"):
                url_to_tempfile(f"http://127.0.0.1:{port}/big.bin", suffix=".bin")
        finally:
            httpd.shutdown()
