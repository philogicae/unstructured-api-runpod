# unstructured-api-runpod

[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://docs.astral.sh/uv/getting-started/installation/)
[![Python](https://img.shields.io/badge/python-3.14%2B-blue)](https://www.python.org/downloads/)
[![Actions status](https://github.com/philogicae/unstructured-api-runpod/actions/workflows/ci-cd.yml/badge.svg?cache-control=no-cache)](https://github.com/philogicae/unstructured-api-runpod/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/philogicae/unstructured-api-runpod)

Document parsing/OCR API powered by [unstructured](https://github.com/Unstructured-IO/unstructured). Supports PDF, DOCX, PPTX, images, HTML, EPUB, and [many more](https://docs.unstructured.io/open-source/introduction/supported-file-types).

Designed to run on [RunPod serverless](https://www.runpod.io/) or as a **standalone FastAPI server**.

[![Runpod](https://api.runpod.io/badge/philogicae/unstructured-api-runpod)](https://console.runpod.io/hub/philogicae/unstructured-api-runpod)

## Quick start

```bash
# Install system dependencies
apt update -y
apt install -y g++ libmagic-dev poppler-utils tesseract-ocr tesseract-ocr-eng tesseract-ocr-osd libreoffice rustc wget
# Install Python dependencies
uv sync
# Run the server on :8000
uv run -m unstructured-api --mode api
```

## Docker

```bash
# Deploy (with rebuild)
docker compose up -d --build
# Test
curl -X POST http://localhost:8000/extract -F "file=@doc.pdf" -o output.zip
```

Deployment is handled via CI — tag a commit and push. See `.github/workflows/ci-cd.yml`.

- `Dockerfile` — serverless (RunPod) mode
- `Dockerfile.test` — standalone API mode (used by `compose.yml` and CI)

## API

**`GET /formats`**: Returns supported file types.

**`POST /extract`**:
| Field | Type | Description |
| ------------- | ---------- | --------------------------------------- |
| `file` | UploadFile | Attach a file directly (multipart only) |
| `file_base64` | str | Base64-encoded file content |
| `file_url` | str | Public URL to download |

## Serverless (RunPod)

```json
{ "input": { "file_base64": "<base64>", "file_url": "https://..." } }
```

## Output

Returns a `.zip` file (`Content-Type: application/zip`) containing:

- `elements.json` — serialized elements array
- `metadata.json` — processing metadata (filename, num_elements, num_pages, etc.)
- `images/` — extracted images (if any)

On error: `{"error": "..."}`
