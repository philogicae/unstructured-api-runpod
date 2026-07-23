from base64 import b64decode
from unittest.mock import patch

import pytest

from unstructured_api.worker import INPUT_SCHEMA, handler


class TestInputSchema:
    def test_has_file_base64(self):
        assert "file_base64" in INPUT_SCHEMA
        assert INPUT_SCHEMA["file_base64"]["type"] is str
        assert INPUT_SCHEMA["file_base64"]["required"] is False

    def test_has_file_url(self):
        assert "file_url" in INPUT_SCHEMA
        assert INPUT_SCHEMA["file_url"]["type"] is str
        assert INPUT_SCHEMA["file_url"]["required"] is False


@pytest.fixture(autouse=True)
def _reset_checkpoints():
    from runpod.serverless.utils.rp_debugger import Checkpoints

    Checkpoints().clear()
    yield
    Checkpoints().clear()


class TestHandler:
    @patch("unstructured_api.worker.parse_document")
    def test_valid_base64_input(self, mock_parse):
        mock_parse.return_value = b"zip-content"
        job = {"input": {"file_base64": "aGVsbG8="}}
        result = handler(job)
        assert isinstance(result, dict)
        assert b64decode(result["zip"]) == b"zip-content"
        assert "total_time" in result

    @patch("unstructured_api.worker.parse_document")
    def test_valid_url_input(self, mock_parse):
        mock_parse.return_value = b"zip-content"
        job = {"input": {"file_url": "https://example.com/doc.pdf"}}
        result = handler(job)
        assert isinstance(result, dict)
        assert b64decode(result["zip"]) == b"zip-content"
        assert "total_time" in result

    def test_invalid_schema(self):
        job = {"input": {"invalid_field": "value"}}
        result = handler(job)
        assert isinstance(result, dict)
        assert "error" in result
        assert "total_time" in result

    @patch("unstructured_api.worker.parse_document")
    def test_oversized_base64(self, mock_parse):
        mock_parse.return_value = b"zip-content"
        big = "a" * int((11 * 1024 * 1024) * 4 / 3)
        job = {"input": {"file_base64": big}}
        result = handler(job)
        assert isinstance(result, dict)
        assert "error" in result
        assert "exceeds max" in result["error"]
        assert "total_time" in result

    @patch("unstructured_api.worker.parse_document")
    @patch("unstructured_api.worker.rp_cleanup")
    def test_exception_cleans_up(self, mock_cleanup, mock_parse):
        mock_parse.side_effect = RuntimeError("boom")
        job = {"input": {"file_base64": "aGVsbG8="}}
        with pytest.raises(RuntimeError):
            handler(job)
        mock_cleanup.clean.assert_called_once()

    @patch("unstructured_api.worker.parse_document")
    @patch("unstructured_api.worker.rp_cleanup")
    def test_success_cleans_up(self, mock_cleanup, mock_parse):
        mock_parse.return_value = b"zip"
        job = {"input": {"file_base64": "aGVsbG8="}}
        handler(job)
        mock_cleanup.clean.assert_called_once()
