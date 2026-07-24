from base64 import b64encode
from unittest.mock import MagicMock, patch

import pytest
from unstructured.documents.elements import ElementMetadata, Text

from unstructured_api.process.document import (
    clean_text,
    cleanup_elements,
    create_result_zip,
    extract,
    filter_elements,
    is_image_too_small,
    parse_document,
    partitioner,
    serialize_element,
    serialize_elements,
)


class TestPartitioner:
    @patch(
        "unstructured_api.process.document.detect_content_type",
        return_value="application/pdf",
    )
    @patch("unstructured_api.process.document.partition")
    def test_partition_pdf(self, mock_partition, mock_ct):
        el = Text("test")
        el.category = "Text"
        mock_partition.return_value = [el]
        result = partitioner("/path/file.pdf", "/tmp/out")
        assert len(result) == 1

    @patch(
        "unstructured_api.process.document.detect_content_type",
        return_value="text/plain",
    )
    @patch("unstructured_api.process.document.partition")
    def test_partition_non_pdf(self, mock_partition, mock_ct):
        el = Text("test")
        el.category = "Text"
        mock_partition.return_value = [el]
        result = partitioner("/path/file.txt", "/tmp/out")
        assert len(result) == 1

    @patch(
        "unstructured_api.process.document.detect_content_type",
        return_value=None,
    )
    @patch("unstructured_api.process.document.partition")
    def test_partition_unsupported_format_without_mime(self, mock_partition, mock_ct):
        from unstructured.partition.common import UnsupportedFileFormatError

        mock_partition.side_effect = UnsupportedFileFormatError("unsupported")
        with pytest.raises(UnsupportedFileFormatError):
            partitioner("/path/file.xyz", "/tmp/out")

    @patch(
        "unstructured_api.process.document.detect_content_type",
        return_value="application/pdf",
    )
    @patch("unstructured_api.process.document.FileType")
    @patch("unstructured_api.process.document._PartitionerLoader")
    @patch("unstructured_api.process.document.partition")
    def test_partition_fallback(
        self, mock_partition, mock_loader, mock_filetype, mock_ct
    ):
        from unstructured.partition.common import UnsupportedFileFormatError

        mock_partition.side_effect = UnsupportedFileFormatError("unsupported")
        ft_instance = MagicMock()
        ft_instance.is_partitionable = True
        mock_filetype.from_mime_type.return_value = ft_instance
        loader_instance = MagicMock()
        fallback_fn = MagicMock(return_value=[Text("fallback")])
        loader_instance.get.return_value = fallback_fn
        mock_loader.return_value = loader_instance
        result = partitioner("/path/file.pdf", "/tmp/out")
        assert len(result) == 1

    @patch(
        "unstructured_api.process.document.detect_content_type",
        return_value="application/pdf",
    )
    @patch("unstructured_api.process.document.partition")
    def test_image_with_text_as_html_converted_to_text(self, mock_partition, mock_ct):
        from unstructured.documents.elements import ElementMetadata

        el = MagicMock(spec=Text)
        el.category = "Image"
        el.metadata = ElementMetadata(
            image_path=None, text_as_html="<table><tr><td>data</td></tr></table>"
        )
        mock_partition.return_value = [el]
        result = partitioner("/path/file.pdf", "/tmp/out")
        assert result[0].category == "UncategorizedText"
        assert result[0].text == "<table><tr><td>data</td></tr></table>"


class TestCleanText:
    def test_empty_string(self):
        assert clean_text("") == ""

    def test_cleans_and_lowercases(self):
        result = clean_text("  Hello---World!  ")
        assert result == "hello world!"

    def test_replaces_unicode_quotes(self):
        result = clean_text("\u201cHello\u201d")
        assert "hello" in result

    def test_removes_bullets(self):
        result = clean_text("\u2022 bullet")
        assert "bullet" in result


class TestCleanupElements:
    def test_applies_clean_to_all(self, sample_text_element):
        el = sample_text_element
        el.text = "  UPPER  "
        cleanup_elements([el])
        assert el.text == "upper"


class TestIsImageTooSmall:
    @patch("unstructured_api.process.document.PILImage.open")
    def test_too_small(self, mock_open):
        img = MagicMock()
        img.width = 10
        img.height = 10
        mock_open.return_value.__enter__.return_value = img
        assert is_image_too_small("/path/img.png") is True

    @patch("unstructured_api.process.document.PILImage.open")
    def test_large_enough(self, mock_open):
        img = MagicMock()
        img.width = 100
        img.height = 100
        mock_open.return_value.__enter__.return_value = img
        assert is_image_too_small("/path/img.png") is False

    @patch("unstructured_api.process.document.PILImage.open")
    def test_exception_returns_false(self, mock_open):
        mock_open.side_effect = Exception("corrupt")
        assert is_image_too_small("/path/img.png") is False


class TestFilterElements:
    def test_passes_through_text_element(self, sample_text_element, temp_dir):
        result = filter_elements([sample_text_element], temp_dir)
        assert len(result) == 1
        assert result[0].category == "Text"

    def test_keeps_unique_image(self, sample_image_element, temp_dir):
        result = filter_elements([sample_image_element], temp_dir)
        assert len(result) == 1

    @patch("unstructured_api.process.document.is_image_too_small", return_value=True)
    def test_removes_small_image(self, mock_small, sample_image_element, temp_dir):
        result = filter_elements([sample_image_element], temp_dir)
        assert len(result) == 0

    @patch("unstructured_api.process.document.find_duplicate_images")
    def test_removes_duplicate_image(self, mock_dupes, sample_image_element, temp_dir):
        mock_dupes.return_value = {"/tmp/test_images/img_1.png"}
        result = filter_elements([sample_image_element], temp_dir)
        assert len(result) == 0

    def test_converts_table_to_image(self, sample_table_element, temp_dir):
        result = filter_elements([sample_table_element], temp_dir)
        assert len(result) == 1
        assert result[0].category == "Image"

    @patch("unstructured_api.process.document.find_duplicate_images")
    def test_duplicate_table_with_html_downgraded_to_text(self, mock_ct, temp_dir):
        meta = ElementMetadata(
            image_path="/tmp/test_images/t1.png",
            text_as_html="<table>html</table>",
            page_number=1,
            filename="test.pdf",
            filetype="application/pdf",
        )
        el = MagicMock(spec=Text)
        el.category = "Table"
        el.text = "original"
        el.metadata = meta
        with patch(
            "unstructured_api.process.document.find_duplicate_images",
            return_value={"/tmp/test_images/t1.png"},
        ):
            result = filter_elements([el], temp_dir)
            assert len(result) == 1
            assert result[0].category == "UncategorizedText"
            assert result[0].text == "<table>html</table>"

    @patch("unstructured_api.process.document.find_duplicate_images")
    def test_duplicate_table_without_html_stays_table(self, mock_ct, temp_dir):
        meta = ElementMetadata(
            image_path="/tmp/test_images/t1.png",
            text_as_html=None,
            page_number=1,
            filename="test.pdf",
            filetype="application/pdf",
        )
        el = MagicMock(spec=Text)
        el.category = "Table"
        el.text = "original"
        el.metadata = meta
        with patch(
            "unstructured_api.process.document.find_duplicate_images",
            return_value={"/tmp/test_images/t1.png"},
        ):
            result = filter_elements([el], temp_dir)
            assert len(result) == 1
            assert result[0].category == "Table"


class TestSerializeElement:
    def test_without_image_path(self):
        meta = ElementMetadata(
            page_number=1,
            filename="test.pdf",
            filetype="application/pdf",
        )
        el = Text(text="hello", metadata=meta)
        el.category = "Text"
        result = serialize_element(el)
        assert result["type"] == "Text"
        assert result["text"] == "hello"
        assert result["metadata"]["image_path"] is None

    def test_with_image_path(self):
        meta = ElementMetadata(
            page_number=2,
            filename="doc.pdf",
            filetype="application/pdf",
            image_path="path/to/img.png",
            image_base64="base64data",
            text_as_html="<html>",
            link_urls=["https://example.com"],
            link_texts=["example"],
            languages=["eng"],
            is_continuation=False,
        )
        el = Text(text="world", metadata=meta)
        el.category = "Title"
        result = serialize_element(el)
        assert result["type"] == "Title"
        assert result["metadata"]["page_number"] == 2
        assert result["metadata"]["text_as_html"] == "<html>"


class TestSerializeElements:
    def test_empty(self):
        assert serialize_elements([]) == []

    def test_multiple(self, sample_elements):
        result = serialize_elements(sample_elements)
        assert len(result) == 3


class TestCreateResultZip:
    def test_basic_zip(self, sample_serialized, temp_dir):
        metadata = {"filename": "test.pdf", "num_elements": 2, "num_pages": 1}
        result = create_result_zip(sample_serialized, metadata, temp_dir)
        import zipfile
        from io import BytesIO

        with zipfile.ZipFile(BytesIO(result)) as zf:
            assert "elements.json" in zf.namelist()
            assert "metadata.json" in zf.namelist()

    def test_zip_with_images(self, sample_serialized, tmp_path):
        images_dir = str(tmp_path / "with_images")
        from pathlib import Path

        Path(images_dir).mkdir(parents=True)
        (Path(images_dir) / "img_1.png").write_text("fake-png")
        sample_serialized[1]["metadata"]["image_path"] = "images/img_1.png"
        metadata = {"filename": "test.pdf", "num_elements": 2}
        result = create_result_zip(sample_serialized, metadata, images_dir)
        import zipfile
        from io import BytesIO

        with zipfile.ZipFile(BytesIO(result)) as zf:
            assert "images/img_1.png" in zf.namelist()


class TestParseDocument:
    @patch("unstructured_api.process.document.base64_to_tempfile")
    @patch("unstructured_api.process.document.extract")
    def test_with_file_content(self, mock_extract, mock_b64tf):
        mock_b64tf.return_value = "/tmp/test_suffix"
        mock_extract.return_value = []
        with patch("unstructured_api.process.document.Path.exists", return_value=False):
            result = parse_document(
                file_content=b64encode(b"hello").decode(), filename="test.pdf"
            )
        assert isinstance(result, bytes)

    @patch("unstructured_api.process.document.url_to_tempfile")
    @patch("unstructured_api.process.document.extract")
    def test_with_file_url(self, mock_extract, mock_url):
        mock_url.return_value = "/tmp/test_suffix"
        mock_extract.return_value = []
        with patch("unstructured_api.process.document.Path.exists", return_value=False):
            result = parse_document(
                file_url="https://example.com/doc.pdf", filename="doc.pdf"
            )
        assert isinstance(result, bytes)

    @patch("unstructured_api.process.document.extract")
    def test_with_file_path(self, mock_extract, temp_file):
        mock_extract.return_value = []
        result = parse_document(file_path=temp_file, filename="test.txt")
        assert isinstance(result, bytes)

    def test_no_input(self):
        result = parse_document()
        assert isinstance(result, dict)
        assert "error" in result

    @patch("unstructured_api.process.document.base64_to_tempfile")
    @patch("unstructured_api.process.document.extract")
    def test_extract_exception_returns_error(self, mock_extract, mock_b64tf):
        mock_b64tf.return_value = "/tmp/file"
        mock_extract.side_effect = ValueError("something broke")
        result = parse_document(file_content=b64encode(b"x").decode())
        assert isinstance(result, dict)
        assert "error" in result
        assert "ValueError" in result["error"]

    def test_integration_with_file_path(self, temp_file):
        result = parse_document(file_path=temp_file, filename="test.txt")
        assert isinstance(result, bytes)


class TestExtract:
    @patch("unstructured_api.process.document.partitioner")
    @patch("unstructured_api.process.document.cleanup_elements")
    @patch("unstructured_api.process.document.filter_elements")
    def test_pipeline(self, mock_filter, mock_cleanup, mock_part):
        mock_part.return_value = [Text("a")]
        mock_cleanup.return_value = [Text("b")]
        mock_filter.return_value = [Text("c")]
        result = extract("/source", "/images", "test.txt")
        assert len(result) == 1
