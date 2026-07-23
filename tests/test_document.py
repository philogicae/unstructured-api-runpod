import io
import json
import os
import tempfile
from base64 import b64encode
from http.server import HTTPServer, SimpleHTTPRequestHandler
from os import path, remove
from shutil import rmtree
from tempfile import NamedTemporaryFile, mkdtemp
from threading import Thread
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

import pytest
from PIL import Image
from unstructured.partition.common import UnsupportedFileFormatError

from unstructured_api.process.document import (
    _create_result_zip,
    _natural_sort,
    clean_text,
    cleanup_elements,
    extract,
    filter_elements,
    find_duplicate_images,
    is_image_too_small,
    parse_document,
    partitioner,
    serialize_element,
    serialize_elements,
)

SAMPLE_CONTENT = b"Hello, world!\n\nThis is a test document.\n"


def _b64(content: bytes = SAMPLE_CONTENT) -> str:
    return b64encode(content).decode("utf-8")


def _decode_zip(zip_bytes: bytes) -> list[dict]:
    with ZipFile(io.BytesIO(zip_bytes)) as zf:
        return json.loads(zf.read("elements.json"))


def _mock_element(
    text: str = "hello",
    category: str = "Text",
    page_number: int | None = 1,
    filename: str = "test.txt",
    filetype: str = "text/plain",
) -> MagicMock:
    el = MagicMock()
    el.category = category
    el.text = text
    el.metadata.page_number = page_number
    el.metadata.filename = filename
    el.metadata.filetype = filetype
    el.metadata.image_path = None
    el.metadata.image_base64 = None
    el.metadata.text_as_html = None
    el.metadata.link_urls = None
    el.metadata.link_texts = None
    el.metadata.languages = ["eng"]
    el.metadata.is_continuation = False
    return el


@patch("unstructured_api.process.document.extract", return_value=[_mock_element()])
def test_parse_base64(mock_extract):
    result = parse_document(file_content=_b64())
    assert isinstance(result, bytes)
    data = _decode_zip(result)
    assert "hello" in data[0]["text"].lower()


@patch("unstructured_api.process.document.extract", return_value=[_mock_element()])
def test_parse_file_path(mock_extract):
    with NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(SAMPLE_CONTENT)
        path = f.name
    try:
        result = parse_document(file_path=path)
        assert isinstance(result, bytes)
        data = _decode_zip(result)
        assert len(data) > 0
    finally:
        remove(path)


def test_parse_no_input():
    result = parse_document()
    assert result == {"error": "No input provided"}


@patch("unstructured_api.process.document.extract", return_value=[_mock_element()])
def test_parse_response_shape(mock_extract):
    result = parse_document(file_content=_b64())
    assert isinstance(result, bytes)
    data = _decode_zip(result)
    assert isinstance(data, list)
    if data:
        assert "type" in data[0]
        assert "text" in data[0]
        assert "metadata" in data[0]


def test_parse_missing_file_path():
    result = parse_document(file_path="/nonexistent/path/file.txt")
    assert isinstance(result, dict)
    assert "error" in result


def test_parse_content_with_invalid_base64():
    result = parse_document(file_content="not-valid-base64!!!")
    assert isinstance(result, dict)
    assert "error" in result


@patch("unstructured_api.process.document.extract", side_effect=ValueError("bad pdf"))
def test_parse_error_does_not_leak_internal_paths(mock_extract):

    bad_pdf = b64encode(
        b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    ).decode()
    result = parse_document(file_content=bad_pdf)
    assert isinstance(result, dict)
    assert "error" in result
    assert "/tmp/" not in result["error"]


def test_is_image_too_small_with_tiny_image():
    with NamedTemporaryFile(suffix=".png", delete=False) as f:
        img_path = f.name
    try:
        img = Image.new("RGB", (10, 10), color="red")
        img.save(img_path)
        assert is_image_too_small(img_path) is True
    finally:
        remove(img_path)


def test_is_image_too_small_with_large_image():
    with NamedTemporaryFile(suffix=".png", delete=False) as f:
        img_path = f.name
    try:
        img = Image.new("RGB", (100, 100), color="red")
        img.save(img_path)
        assert is_image_too_small(img_path) is False
    finally:
        remove(img_path)


def test_is_image_too_small_nonexistent():
    assert is_image_too_small("/nonexistent/image.png") is False


def test_serialize_element_keys():
    mock_element = MagicMock()
    mock_element.category = "Title"
    mock_element.text = "Hello"
    mock_element.metadata.page_number = 1
    mock_element.metadata.filename = "test.pdf"
    mock_element.metadata.filetype = "application/pdf"
    mock_element.metadata.image_path = None
    mock_element.metadata.image_base64 = None
    mock_element.metadata.text_as_html = None
    mock_element.metadata.link_urls = None
    mock_element.metadata.link_texts = None
    mock_element.metadata.languages = ["eng"]
    mock_element.metadata.is_continuation = False

    result = serialize_element(mock_element)
    assert result["type"] == "Title"
    assert result["text"] == "Hello"
    assert "metadata" in result
    assert result["metadata"]["page_number"] == 1
    assert result["metadata"]["filename"] == "test.pdf"
    assert result["metadata"]["languages"] == ["eng"]


def test_natural_sort():
    files = ["img10.png", "img2.png", "img1.png"]
    assert _natural_sort(files) == ["img1.png", "img2.png", "img10.png"]


def test_find_duplicate_images_empty_dir():

    assert find_duplicate_images(mkdtemp()) == set()


def test_find_duplicate_images_with_duplicates():

    img_dir = mkdtemp()
    try:
        img = Image.new("RGB", (50, 50), color="blue")
        img.save(path.join(img_dir, "img1.png"))
        img.save(path.join(img_dir, "img2.png"))
        dups = find_duplicate_images(img_dir)
        assert len(dups) == 1
    finally:
        rmtree(img_dir, ignore_errors=True)


def test_clean_text_empty():
    assert clean_text("") == ""


def test_clean_text_normal():
    result = clean_text("  Hello   World  ")
    assert "hello" in result
    assert "world" in result


def test_cleanup_elements():
    mock_el = MagicMock()
    mock_el.text = "  Hello  "
    mock_el.apply = lambda fn: setattr(mock_el, "text", fn(mock_el.text))
    result = cleanup_elements([mock_el])
    assert len(result) == 1


def test_filter_elements_table_becomes_image():
    mock_el = MagicMock()
    mock_el.category = "Table"
    mock_el.text = "table text"
    mock_el.metadata.image_path = None

    img_dir = mkdtemp()
    try:
        result = filter_elements([mock_el], img_dir)
        assert len(result) == 1
        assert result[0].category == "Image"
    finally:
        rmtree(img_dir, ignore_errors=True)


def test_filter_elements_removes_small_image():

    img_dir = mkdtemp()
    try:
        img_path = path.join(img_dir, "small.png")
        img = Image.new("RGB", (10, 10), color="red")
        img.save(img_path)

        mock_el = MagicMock()
        mock_el.category = "Image"
        mock_el.text = ""
        mock_el.metadata.image_path = img_path

        result = filter_elements([mock_el], img_dir)
        assert len(result) == 0
        assert not path.exists(img_path)
    finally:
        rmtree(img_dir, ignore_errors=True)


def test_filter_elements_keeps_normal_image():

    img_dir = mkdtemp()
    try:
        img_path = path.join(img_dir, "big.png")
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(img_path)

        mock_el = MagicMock()
        mock_el.category = "Image"
        mock_el.text = ""
        mock_el.metadata.image_path = img_path

        result = filter_elements([mock_el], img_dir)
        assert len(result) == 1
    finally:
        rmtree(img_dir, ignore_errors=True)


@patch("unstructured_api.process.document.partitioner", return_value=[_mock_element()])
def test_extract_with_text_file(mock_partitioner):
    with NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(SAMPLE_CONTENT)
        file_path = f.name
    try:
        images_dir = mkdtemp()
        try:
            elements = extract(file_path, images_dir)
            assert len(elements) > 0
        finally:
            rmtree(images_dir, ignore_errors=True)
    finally:
        remove(file_path)


def test_create_result_zip_with_images():

    img_dir = mkdtemp()
    try:
        img = Image.new("RGB", (50, 50), color="green")
        img.save(path.join(img_dir, "photo.png"))

        serialized = [
            {
                "type": "Image",
                "text": "",
                "metadata": {
                    "image_path": path.join(img_dir, "photo.png"),
                    "page_number": 1,
                },
            }
        ]
        metadata = {"filename": "test.pdf", "num_elements": 1}
        zip_bytes = _create_result_zip(serialized, metadata, img_dir)
        with ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            assert "elements.json" in names
            assert "metadata.json" in names
            assert "images/photo.png" in names
            data = json.loads(zf.read("elements.json"))
            assert data[0]["metadata"]["image_path"] == "images/photo.png"
            meta = json.loads(zf.read("metadata.json"))
            assert meta["filename"] == "test.pdf"
    finally:
        rmtree(img_dir, ignore_errors=True)


def test_create_result_zip_no_images_dir():
    serialized = [{"type": "Text", "text": "hello", "metadata": {"image_path": None}}]
    metadata = {"filename": "test.txt", "num_elements": 1}
    zip_bytes = _create_result_zip(serialized, metadata, "/nonexistent/dir")
    with ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert "elements.json" in names
        assert "metadata.json" in names


@patch("unstructured_api.process.document.extract", return_value=[_mock_element()])
def test_parse_document_with_file_url(mock_extract):

    handler = SimpleHTTPRequestHandler
    httpd = HTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        test_dir = tempfile.mkdtemp()
        test_file = path.join(test_dir, "test.txt")
        with open(test_file, "wb") as f:
            f.write(SAMPLE_CONTENT)

        cwd = os.getcwd()
        os.chdir(test_dir)
        try:
            result = parse_document(file_url=f"http://127.0.0.1:{port}/test.txt")
            assert isinstance(result, bytes)
            data = _decode_zip(result)
            assert len(data) > 0
        finally:
            os.chdir(cwd)

            rmtree(test_dir, ignore_errors=True)
    finally:
        httpd.shutdown()


def test_serialize_elements_list():
    mock_el = MagicMock()
    mock_el.category = "Title"
    mock_el.text = "Hello"
    mock_el.metadata.page_number = 1
    mock_el.metadata.filename = "test.pdf"
    mock_el.metadata.filetype = "application/pdf"
    mock_el.metadata.image_path = None
    mock_el.metadata.image_base64 = None
    mock_el.metadata.text_as_html = None
    mock_el.metadata.link_urls = None
    mock_el.metadata.link_texts = None
    mock_el.metadata.languages = ["eng"]
    mock_el.metadata.is_continuation = False

    result = serialize_elements([mock_el])
    assert len(result) == 1
    assert result[0]["type"] == "Title"


def test_filter_elements_oserror_on_remove():

    img_dir = mkdtemp()
    try:
        mock_el = MagicMock()
        mock_el.category = "Image"
        mock_el.text = ""
        mock_el.metadata.image_path = "/nonexistent/path/image.png"

        with patch("unstructured_api.process.document.remove", side_effect=OSError):
            result = filter_elements([mock_el], img_dir)
        assert len(result) == 1
    finally:
        rmtree(img_dir, ignore_errors=True)


@patch(
    "unstructured_api.process.document.extract",
    return_value=[
        _mock_element(
            text="page content",
            page_number=3,
            filename="test.pdf",
            filetype="application/pdf",
        )
    ],
)
def test_parse_document_num_pages(mock_extract):
    result = parse_document(file_content=_b64())
    assert isinstance(result, bytes)
    with ZipFile(io.BytesIO(result)) as zf:
        meta = json.loads(zf.read("metadata.json"))
    assert meta["num_pages"] == 3


def test_partitioner_pdf_path():
    with NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4 fake pdf")
        pdf_path = f.name
    try:
        images_dir = mkdtemp()
        try:
            with (
                patch("unstructured.partition.auto.partition") as mock_part,
                patch(
                    "unstructured_api.process.document.detect_content_type",
                    return_value="application/pdf",
                ),
            ):
                mock_part.return_value = []
                result = partitioner(pdf_path, images_dir)
                assert result == []
                call_kwargs = mock_part.call_args[1]
                assert call_kwargs["extract_images_in_pdf"] is True
                assert call_kwargs["extract_image_block_output_dir"] == images_dir
        finally:
            rmtree(images_dir, ignore_errors=True)
    finally:
        remove(pdf_path)


def test_partitioner_unsupported_format_fallback():

    mock_element = MagicMock()
    mock_element.category = "Text"
    mock_element.text = "hello"
    mock_element.metadata.image_path = None
    mock_element.metadata.text_as_html = None

    fallback_fn = MagicMock(return_value=[mock_element])

    with (
        patch(
            "unstructured.partition.auto.partition",
            side_effect=UnsupportedFileFormatError,
        ),
        patch(
            "unstructured_api.process.document.detect_content_type",
            return_value="text/plain",
        ),
        patch("unstructured.partition.auto._PartitionerLoader") as mock_loader,
    ):
        mock_loader.return_value.get.return_value = fallback_fn
        with NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(SAMPLE_CONTENT)
            txt_path = f.name
        try:
            result = partitioner(txt_path, "/tmp")
            assert len(result) == 1
            mock_loader.return_value.get.assert_called_once()
        finally:
            remove(txt_path)


def test_partitioner_unsupported_format_not_partitionable():

    with (
        patch(
            "unstructured.partition.auto.partition",
            side_effect=UnsupportedFileFormatError,
        ),
        patch(
            "unstructured_api.process.document.detect_content_type",
            return_value="application/x-unknown",
        ),
    ):
        with NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"unknown")
            xyz_path = f.name
        try:
            with pytest.raises(UnsupportedFileFormatError):
                partitioner(xyz_path, "/tmp")
        finally:
            remove(xyz_path)


def test_partitioner_text_as_html_conversion():
    mock_element = MagicMock()
    mock_element.category = "Table"
    mock_element.text = ""
    mock_element.metadata.image_path = None
    mock_element.metadata.text_as_html = "<table><tr><td>A</td></tr></table>"

    with (
        patch("unstructured.partition.auto.partition", return_value=[mock_element]),
        patch(
            "unstructured_api.process.document.detect_content_type",
            return_value="text/plain",
        ),
    ):
        with NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(SAMPLE_CONTENT)
            txt_path = f.name
        try:
            result = partitioner(txt_path, "/tmp")
            assert len(result) == 1
            assert "<table>" in result[0].text
        finally:
            remove(txt_path)


def test_filter_elements_removes_duplicate_image():

    img_dir = mkdtemp()
    try:
        img_path = path.join(img_dir, "img1.png")
        img = Image.new("RGB", (100, 100), color="red")
        img.save(img_path)

        mock_el = MagicMock()
        mock_el.category = "Image"
        mock_el.text = ""
        mock_el.metadata.image_path = img_path

        with patch(
            "unstructured_api.process.document.find_duplicate_images",
            return_value={img_path},
        ):
            result = filter_elements([mock_el], img_dir)
        assert len(result) == 0
        assert not path.exists(img_path)
    finally:
        rmtree(img_dir, ignore_errors=True)


def test_filter_elements_duplicate_image_oserror():

    img_dir = mkdtemp()
    try:
        mock_el = MagicMock()
        mock_el.category = "Image"
        mock_el.text = ""
        mock_el.metadata.image_path = "/nonexistent/image.png"

        with (
            patch(
                "unstructured_api.process.document.find_duplicate_images",
                return_value={"/nonexistent/image.png"},
            ),
            patch(
                "unstructured_api.process.document.remove",
                side_effect=OSError("permission denied"),
            ),
        ):
            result = filter_elements([mock_el], img_dir)
        assert len(result) == 0
    finally:
        rmtree(img_dir, ignore_errors=True)


def test_filter_elements_duplicate_table_falls_back_to_text():

    img_dir = mkdtemp()
    try:
        img_path = path.join(img_dir, "table_img.png")
        img = Image.new("RGB", (100, 100), color="red")
        img.save(img_path)

        mock_el = MagicMock()
        mock_el.category = "Table"
        mock_el.text = ""
        mock_el.metadata.image_path = img_path
        mock_el.metadata.text_as_html = "<table><tr><td>A</td></tr></table>"

        with patch(
            "unstructured_api.process.document.find_duplicate_images",
            return_value={img_path},
        ):
            result = filter_elements([mock_el], img_dir)
        assert len(result) == 1
        assert result[0].text == "<table><tr><td>A</td></tr></table>"
    finally:
        rmtree(img_dir, ignore_errors=True)


def test_parse_document_with_page_numbers():
    mock_element = MagicMock()
    mock_element.category = "Text"
    mock_element.text = "page content"
    mock_element.metadata.image_path = None
    mock_element.metadata.text_as_html = None
    mock_element.metadata.page_number = 3
    mock_element.metadata.filename = "test.pdf"
    mock_element.metadata.filetype = "application/pdf"
    mock_element.metadata.image_base64 = None
    mock_element.metadata.link_urls = None
    mock_element.metadata.link_texts = None
    mock_element.metadata.languages = ["eng"]
    mock_element.metadata.is_continuation = False

    with patch(
        "unstructured_api.process.document.extract", return_value=[mock_element]
    ):
        result = parse_document(file_content=_b64())
        assert isinstance(result, bytes)
        with ZipFile(io.BytesIO(result)) as zf:
            meta = json.loads(zf.read("metadata.json"))
        assert meta["num_pages"] == 3
