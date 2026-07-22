from os import path

from unstructured_api.process.utils import base64_to_tempfile, cleanup, guess_suffix


def test_base64_to_tempfile_roundtrip():
    original = b"hello world test content"
    from base64 import b64encode

    b64 = b64encode(original).decode("utf-8")
    temp = base64_to_tempfile(b64, suffix=".txt")
    try:
        with open(temp, "rb") as f:
            assert f.read() == original
    finally:
        cleanup(temp)
    assert not path.exists(temp)


def test_base64_to_tempfile_with_suffix():
    from base64 import b64encode

    b64 = b64encode(b"test").decode("utf-8")
    temp = base64_to_tempfile(b64, suffix=".pdf")
    try:
        assert temp.endswith(".pdf")
    finally:
        cleanup(temp)


def test_cleanup_nonexistent():
    cleanup("/tmp/nonexistent_file_12345")
    assert True


def test_guess_suffix():
    assert guess_suffix("doc.pdf") == ".pdf"
    assert guess_suffix("doc.PDF") == ".PDF"
    assert guess_suffix("image.png") == ".png"
    assert guess_suffix("") == ""
    assert guess_suffix(None) == ""
    assert guess_suffix("noext") == ""
