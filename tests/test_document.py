from base64 import b64encode
from tempfile import NamedTemporaryFile

from unstructured_api.process.document import parse_document

SAMPLE_CONTENT = b"Hello, world!\n\nThis is a test document.\n"


def _b64(content: bytes = SAMPLE_CONTENT) -> str:
    return b64encode(content).decode("utf-8")


def test_parse_base64():
    result = parse_document(file_content=_b64(), filename="hello.txt")
    assert result["error"] is None
    assert result["metadata"]["num_elements"] > 0
    assert "hello" in result["elements"][0]["text"].lower()


def test_parse_file_path():
    with NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(SAMPLE_CONTENT)
        path = f.name
    try:
        result = parse_document(file_path=path)
        assert result["error"] is None
        assert result["metadata"]["num_elements"] > 0
    finally:
        from os import remove

        remove(path)


def test_parse_no_input():
    result = parse_document()
    assert result["error"] is not None


def test_parse_response_shape():
    result = parse_document(file_content=_b64(), filename="hello.txt")
    assert "elements" in result
    assert "metadata" in result
    assert "error" in result
    assert isinstance(result["elements"], list)
    assert isinstance(result["metadata"], dict)
    if result["elements"]:
        e = result["elements"][0]
        assert "type" in e
        assert "text" in e
        assert "metadata" in e


def test_parse_missing_file_path():
    result = parse_document(file_path="/nonexistent/path/file.txt")
    assert result["error"] is not None
    assert result["elements"] == []


def test_parse_content_with_invalid_base64():
    result = parse_document(file_content="not-valid-base64!!!", filename="test.txt")
    assert result["error"] is not None
