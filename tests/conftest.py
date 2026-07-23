from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from unstructured.documents.elements import ElementMetadata, Image, Text


@pytest.fixture(autouse=True)
def mock_magika():
    with patch("unstructured_api.process.utils.Magika") as mock:
        instance = mock.return_value
        result = MagicMock()
        result.ok = True
        result.output.mime_type = "application/pdf"
        instance.identify_path.return_value = result
        yield


@pytest.fixture(autouse=True)
def mock_phasher():
    with patch("unstructured_api.process.utils.PHash") as mock:
        instance = mock.return_value
        instance.find_duplicates.return_value = {}
        yield


def make_meta(**overrides: Any) -> ElementMetadata:
    meta = ElementMetadata()
    for key, value in {
        "page_number": 1,
        "filename": "test.pdf",
        "filetype": "application/pdf",
        "image_path": None,
        "image_base64": None,
        "text_as_html": None,
        "link_urls": None,
        "link_texts": None,
        "languages": None,
        "is_continuation": None,
        **overrides,
    }.items():
        setattr(meta, key, value)
    return meta


@pytest.fixture
def sample_text_element():
    meta = make_meta()
    el = Text(text="Hello World", metadata=meta)
    el.category = "Text"
    return el


@pytest.fixture
def sample_image_element():
    meta = make_meta(image_path="/tmp/test_images/img_1.png")
    el = Image(text="", metadata=meta)
    el.category = "Image"
    return el


@pytest.fixture
def sample_table_element():
    meta = make_meta(text_as_html="<table><tr><td>data</td></tr></table>")
    el = Image(text="table data", metadata=meta)
    el.category = "Table"
    return el


@pytest.fixture
def sample_elements(sample_text_element, sample_image_element, sample_table_element):
    return [sample_text_element, sample_image_element, sample_table_element]


@pytest.fixture
def sample_serialized():
    return [
        {
            "type": "Text",
            "text": "Hello World",
            "metadata": {
                "page_number": 1,
                "filename": "test.pdf",
                "filetype": "application/pdf",
                "image_path": None,
                "image_base64": None,
                "text_as_html": None,
                "link_urls": None,
                "link_texts": None,
                "languages": None,
                "is_continuation": None,
            },
        },
        {
            "type": "Image",
            "text": "",
            "metadata": {
                "page_number": 1,
                "filename": "test.pdf",
                "filetype": "application/pdf",
                "image_path": "images/img_1.png",
                "image_base64": None,
                "text_as_html": None,
                "link_urls": None,
                "link_texts": None,
                "languages": None,
                "is_continuation": None,
            },
        },
    ]


@pytest.fixture
def temp_dir(tmp_path):
    d = tmp_path / "test_images"
    d.mkdir()
    return str(d)


@pytest.fixture
def temp_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    return str(f)
