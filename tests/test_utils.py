from base64 import b64encode
from unittest.mock import MagicMock, patch

import pytest

from unstructured_api.process.utils import (
    base64_to_tempfile,
    cleanup,
    detect_content_type,
    exceeds_size,
    find_duplicate_images,
    get_filename,
    natural_sort,
    url_to_tempfile,
)
from unstructured_api.settings import MAX_SIZE


class TestGetFilename:
    def test_with_filename(self):
        assert get_filename(filename="doc.pdf") == "doc.pdf"

    def test_with_file_url(self):
        assert get_filename(file_url="https://example.com/doc.pdf") == "doc.pdf"

    def test_with_url_no_filename(self):
        assert get_filename(file_url="https://example.com/") is None

    def test_filename_takes_precedence(self):
        assert (
            get_filename(filename="a.pdf", file_url="https://example.com/b.pdf")
            == "a.pdf"
        )

    def test_no_input(self):
        assert get_filename() is None


class TestExceedsSize:
    def test_bytes_under(self):
        assert exceeds_size(b"small", max_size=100) is False

    def test_bytes_over(self):
        assert exceeds_size(b"x" * 101, max_size=100) is True

    def test_bytes_equal(self):
        assert exceeds_size(b"x" * 100, max_size=100) is False

    def test_str_under(self):
        assert exceeds_size("a" * 100, max_size=100) is False

    def test_str_over(self):
        assert exceeds_size("a" * 134, max_size=100) is True

    def test_str_equal(self):
        assert exceeds_size("a" * 133, max_size=100) is False

    def test_uses_default_max_size(self):
        assert exceeds_size(b"x" * (MAX_SIZE + 1)) is True
        assert exceeds_size(b"x" * MAX_SIZE) is False


class TestNaturalSort:
    def test_mixed_text_and_numbers(self):
        files = ["img_10.png", "img_2.png", "img_1.png"]
        assert natural_sort(files) == ["img_1.png", "img_2.png", "img_10.png"]

    def test_already_sorted(self):
        assert natural_sort(["a", "b", "c"]) == ["a", "b", "c"]

    def test_empty_list(self):
        assert natural_sort([]) == []

    def test_case_insensitive(self):
        assert natural_sort(["B", "a", "C"]) == ["a", "B", "C"]


class TestDetectContentType:
    @patch("unstructured_api.process.utils.magika")
    def test_success(self, mock_magika):
        result = MagicMock()
        result.ok = True
        result.output.mime_type = "application/pdf"
        mock_magika.identify_path.return_value = result
        assert detect_content_type("/path/to/file.pdf") == "application/pdf"

    @patch("unstructured_api.process.utils.magika")
    def test_failure(self, mock_magika):
        mock_magika.identify_path.side_effect = Exception("fail")
        assert detect_content_type("/path/to/file.pdf") is None

    @patch("unstructured_api.process.utils.magika")
    def test_not_ok(self, mock_magika):
        result = MagicMock()
        result.ok = False
        mock_magika.identify_path.return_value = result
        assert detect_content_type("/path/to/file.pdf") is None


class TestBase64ToTempfile:
    def test_creates_tempfile_with_content(self):
        content = b64encode(b"hello world").decode()
        path = base64_to_tempfile(content, suffix=".txt")
        try:
            with open(path) as f:
                assert f.read() == "hello world"
            assert path.endswith(".txt")
        finally:
            cleanup(path)


class TestUrlToTempfile:
    @patch("unstructured_api.process.utils.urlopen")
    def test_downloads_url(self, mock_urlopen):
        response = MagicMock()
        response.headers.get.return_value = None
        response.read.side_effect = [b"hello ", b"world", b""]
        mock_urlopen.return_value.__enter__.return_value = response
        path = url_to_tempfile("https://example.com/file.txt", suffix=".txt")
        try:
            with open(path) as f:
                assert f.read() == "hello world"
            assert path.endswith(".txt")
        finally:
            cleanup(path)

    def test_rejects_non_http_scheme(self):
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            url_to_tempfile("ftp://example.com/file.txt")

    @patch("unstructured_api.process.utils.urlopen")
    def test_rejects_oversized_content_length(self, mock_urlopen):
        response = MagicMock()
        response.headers.get.return_value = str(MAX_SIZE + 1)
        mock_urlopen.return_value.__enter__.return_value = response
        with pytest.raises(ValueError, match="Download exceeds max size"):
            url_to_tempfile("https://example.com/big.txt")

    @patch("unstructured_api.process.utils.urlopen")
    def test_rejects_oversized_download(self, mock_urlopen):
        response = MagicMock()
        response.headers.get.return_value = str(MAX_SIZE // 2)
        big_chunk = b"x" * (MAX_SIZE + 1)
        response.read.side_effect = [big_chunk, b""]
        mock_urlopen.return_value.__enter__.return_value = response
        with pytest.raises(ValueError, match="Download exceeds max size"):
            url_to_tempfile("https://example.com/big.txt")


class TestFindDuplicateImages:
    def test_empty_directory(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir(exist_ok=True)
        assert find_duplicate_images(str(d)) == set()


class TestCleanup:
    def test_removes_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content")
        cleanup(str(f))
        assert not f.exists()

    def test_no_error_on_missing(self, tmp_path):
        cleanup(str(tmp_path / "nonexistent.txt"))
