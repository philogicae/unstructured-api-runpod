import asyncio
import json
from base64 import b64encode
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from unstructured_api.server import app, extract, start
from unstructured_api.settings import MAX_UPLOAD_SIZE

client = TestClient(app)
SAMPLE_CONTENT = b"Hello from test"


def _zip_to_elems(resp) -> list[dict]:
    with ZipFile(BytesIO(resp.content)) as zf:
        return json.loads(zf.read("elements.json"))


def _fake_zip(elements: list[dict]) -> bytes:
    buf = BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr("elements.json", json.dumps(elements))
        zf.writestr("metadata.json", "{}")
    return buf.getvalue()


def test_health():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_formats():
    resp = client.get("/formats")
    assert resp.status_code == 200
    body = resp.json()
    assert "documents" in body
    assert "images" in body
    assert "text" in body
    assert "PDF" in body["documents"]


def test_schema():
    resp = client.get("/schema")
    assert resp.status_code == 200
    body = resp.json()
    assert "schema" in body
    assert "/health" in body["schema"]
    assert "/formats" in body["schema"]
    assert "/extract" in body["schema"]


def test_extract_no_input():
    resp = client.post("/extract")
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is not None


@patch("unstructured_api.server.parse_document")
def test_extract_with_file(mock_parse):
    mock_parse.return_value = _fake_zip(
        [{"type": "Text", "text": "hello", "metadata": {}}]
    )
    resp = client.post(
        "/extract",
        files={"file": ("hello.txt", BytesIO(SAMPLE_CONTENT))},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    elems = _zip_to_elems(resp)
    assert len(elems) > 0


@patch("unstructured_api.server.parse_document")
def test_extract_with_base64(mock_parse):
    mock_parse.return_value = _fake_zip(
        [{"type": "Text", "text": "hello", "metadata": {}}]
    )
    b64 = b64encode(SAMPLE_CONTENT).decode("utf-8")
    resp = client.post("/extract", data={"file_base64": b64})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    elems = _zip_to_elems(resp)
    assert len(elems) > 0


def test_extract_invalid_base64():
    resp = client.post(
        "/extract",
        data={"file_base64": "not-valid-base64!!!"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is not None


def test_cors_headers():
    resp = client.options(
        "/extract",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") is not None


def test_extract_file_too_large():
    big_content = b"x" * (MAX_UPLOAD_SIZE + 1)
    resp = client.post(
        "/extract",
        files={"file": ("big.txt", BytesIO(big_content))},
    )
    assert resp.status_code == 413


def test_extract_base64_too_large():
    big_b64 = "x" * (MAX_UPLOAD_SIZE * 4 // 3 + 1)
    resp = client.post(
        "/extract",
        data={"file_base64": big_b64},
    )
    assert resp.status_code in (400, 413)


def test_server_start():
    with patch("unstructured_api.server.uvicorn") as mock_uvicorn:
        start(host="127.0.0.1", port=9999)
        mock_uvicorn.run.assert_called_once()


def test_extract_base64_size_limit_direct():
    big_b64 = "x" * (MAX_UPLOAD_SIZE * 4 // 3 + 1)
    with patch("unstructured_api.server.parse_document") as mock_parse:
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(extract(file=None, file_base64=big_b64))
        assert exc_info.value.status_code == 413
        mock_parse.assert_not_called()
