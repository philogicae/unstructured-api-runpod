from base64 import b64encode
from io import BytesIO

from fastapi.testclient import TestClient

from unstructured_api.server import app

client = TestClient(app)
SAMPLE_CONTENT = b"Hello from test"


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
    assert "/parse" in body["schema"]


def test_parse_no_input():
    resp = client.post("/parse")
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is not None


def test_parse_with_file():
    resp = client.post(
        "/parse",
        files={"file": ("hello.txt", BytesIO(SAMPLE_CONTENT))},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    assert body["metadata"]["num_elements"] > 0


def test_parse_with_base64():
    b64 = b64encode(SAMPLE_CONTENT).decode("utf-8")
    resp = client.post("/parse", data={"file_base64": b64, "filename": "test.txt"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
