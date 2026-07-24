from base64 import b64encode
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from unstructured_api.server import app
from unstructured_api.settings import SUPPORTED_FORMATS


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestRoot:
    async def test_get_root(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestFormats:
    async def test_get_formats(self, client):
        resp = await client.get("/formats")
        assert resp.status_code == 200
        assert resp.json() == SUPPORTED_FORMATS


class TestExtract:
    @patch("unstructured_api.server.parse_document")
    async def test_with_file_upload(self, mock_parse, client, tmp_path):
        mock_parse.return_value = b"zip-content"
        f = tmp_path / "test.pdf"
        f.write_text("pdf content")
        resp = await client.post(
            "/extract", files={"file": ("test.pdf", f.read_bytes(), "application/pdf")}
        )
        assert resp.status_code == 200
        assert resp.content == b"zip-content"
        assert resp.headers["content-type"] == "application/zip"

    @patch("unstructured_api.server.parse_document")
    async def test_with_base64(self, mock_parse, client):
        mock_parse.return_value = b"zip-content"
        data = b64encode(b"hello").decode()
        resp = await client.post("/extract", data={"file_base64": data})
        assert resp.status_code == 200

    @patch("unstructured_api.server.parse_document")
    async def test_with_file_url(self, mock_parse, client):
        mock_parse.return_value = b"zip-content"
        resp = await client.post(
            "/extract", data={"file_url": "https://example.com/doc.pdf"}
        )
        assert resp.status_code == 200

    async def test_oversized_file_upload(self, client, tmp_path):
        f = tmp_path / "big.pdf"
        big = b"x" * (11 * 1024 * 1024)
        f.write_bytes(big)
        resp = await client.post(
            "/extract", files={"file": ("big.pdf", f.read_bytes(), "application/pdf")}
        )
        assert resp.status_code == 413

    @patch("unstructured_api.server.exceeds_size", return_value=True)
    async def test_oversized_base64(self, mock_exceeds, client):
        resp = await client.post(
            "/extract", data={"file_base64": b64encode(b"x").decode()}
        )
        assert resp.status_code == 413

    @patch("unstructured_api.server.parse_document")
    async def test_no_input_returns_error(self, mock_parse, client):
        mock_parse.return_value = {"error": "No input provided"}
        resp = await client.post("/extract")
        assert resp.status_code == 200
        assert resp.json() == {"error": "No input provided"}

    @patch("unstructured_api.server.parse_document")
    async def test_error_dict_returns_as_json(self, mock_parse, client):
        mock_parse.return_value = {"error": "some error"}
        resp = await client.post(
            "/extract", data={"file_base64": b64encode(b"x").decode()}
        )
        assert resp.status_code == 200
        assert resp.json() == {"error": "some error"}


class TestCORS:
    async def test_cors_headers(self, client):
        resp = await client.options(
            "/",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "*"
