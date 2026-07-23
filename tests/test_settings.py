from unstructured_api.settings import (
    EXTRACT_IMAGE_BLOCK_TYPES,
    MAX_SIZE,
    MIDDLEWARE_PARAMS,
    MIN_IMAGE_PIXELS,
    PDF_IMAGE_DPI,
    SUPPORTED_FORMATS,
    URL_TIMEOUT,
)


def test_constants():
    assert PDF_IMAGE_DPI == 200
    assert EXTRACT_IMAGE_BLOCK_TYPES == ["Image", "Table"]
    assert MIN_IMAGE_PIXELS == 2500
    assert MAX_SIZE == 10 * 1024 * 1024
    assert URL_TIMEOUT == 600


def test_middleware_params():
    assert MIDDLEWARE_PARAMS["allow_origins"] == ["*"]
    assert MIDDLEWARE_PARAMS["allow_methods"] == ["*"]
    assert MIDDLEWARE_PARAMS["allow_headers"] == ["*"]


def test_supported_formats_structure():
    assert "documents" in SUPPORTED_FORMATS
    assert "images" in SUPPORTED_FORMATS
    assert "email" in SUPPORTED_FORMATS
    assert "text" in SUPPORTED_FORMATS
    assert "archives" in SUPPORTED_FORMATS


def test_supported_formats_has_pdf():
    assert "PDF" in SUPPORTED_FORMATS["documents"]
    assert ".pdf" in SUPPORTED_FORMATS["documents"]["PDF"]


def test_supported_formats_has_jpeg():
    assert "JPEG" in SUPPORTED_FORMATS["images"]
    assert ".jpg" in SUPPORTED_FORMATS["images"]["JPEG"]


def test_supported_formats_has_txt():
    assert "Plain Text" in SUPPORTED_FORMATS["text"]
    assert ".txt" in SUPPORTED_FORMATS["text"]["Plain Text"]
