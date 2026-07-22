from unittest.mock import patch

from unstructured_api.worker import handler, INPUT_SCHEMA


def test_handler_schema():
    job = {"input": {"schema": True}}
    result = handler(job)
    assert "schema" in result
    assert "input" in result["schema"]


@patch("unstructured_api.worker.parse_document")
def test_handler_valid(mock_parse):
    mock_parse.return_value = {"elements": [], "metadata": {}, "error": None}
    job = {"input": {"file_base64": "SGVsbG8=", "filename": "test.txt"}}
    result = handler(job)
    assert result["error"] is None
    mock_parse.assert_called_once_with(
        file_content="SGVsbG8=",
        file_url=None,
        filename="test.txt",
    )


@patch("unstructured_api.worker.parse_document")
def test_handler_minimal_input(mock_parse):
    mock_parse.return_value = {"elements": [], "metadata": {}, "error": None}
    job = {"input": {"file_base64": "dGVzdA=="}}
    result = handler(job)
    assert result["error"] is None
    mock_parse.assert_called_once()
    kwargs = mock_parse.call_args[1]
    assert kwargs["file_content"] == "dGVzdA=="
    assert kwargs["filename"] == "document"


def test_handler_missing_input_key():
    job = {"input": {}}
    result = handler(job)
    assert "error" in result


def test_input_schema_structure():
    assert "file_base64" in INPUT_SCHEMA
    assert "file_url" in INPUT_SCHEMA
    assert "filename" in INPUT_SCHEMA
    assert not INPUT_SCHEMA["file_base64"]["required"]
