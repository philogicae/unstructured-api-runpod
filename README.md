# unstructured-api-runpod

[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://docs.astral.sh/uv/getting-started/installation/)
[![Python](https://img.shields.io/badge/python-3.14%2B-blue)](https://www.python.org/downloads/)
[![Actions status](https://github.com/philogicae/unstructured-api-runpod/actions/workflows/ci-cd.yml/badge.svg?cache-control=no-cache)](https://github.com/philogicae/unstructured-api-runpod/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/philogicae/unstructured-api-runpod)

Document parsing/OCR API powered by [unstructured](https://github.com/Unstructured-IO/unstructured). Supports PDF, DOCX, PPTX, images, HTML, EPUB, and [many more](https://docs.unstructured.io/open-source/introduction/supported-file-types).

[![Runpod](https://api.runpod.io/badge/philogicae/unstructured-api-runpod)](https://console.runpod.io/hub/philogicae/unstructured-api-runpod)

Designed to run on [RunPod serverless](https://www.runpod.io/) or as a **standalone FastAPI server**.

## Quick start

```bash
# Install system dependencies
apt update -y
apt install -y g++ libmagic-dev poppler-utils tesseract-ocr libreoffice rustc

# Install Python dependencies
uv sync

# Run the server
uv run -m unstructured-api --mode api    # start FastAPI on :8000
```

## Docker

```bash
docker compose up -d
curl -X POST http://localhost:8000/extract -F "file=@document.pdf"
```

Deployment is handled via CI — tag a commit and push. See `.github/workflows/ci-cd.yml`.

- `Dockerfile` — serverless (RunPod) mode
- `Dockerfile.test` — standalone API mode (used by `compose.yml` and CI)

## API

### POST /extract

Upload a file directly (multipart) or pass base64/URL:

| Field         | Type       | Description                             |
| ------------- | ---------- | --------------------------------------- |
| `file`        | UploadFile | Attach a file directly (multipart only) |
| `file_base64` | str        | Base64-encoded file content             |
| `file_url`    | str        | Public URL to download                  |

Uses `hi_res` strategy with auto-detected OCR languages.

Max upload size: 200 MB. Downloads from URLs are limited to 200 MB.

### GET /formats

Returns all supported file formats categorized by type.

### Serverless (RunPod)

```json
{
  "input": {
    "file_base64": "<base64>",
    "file_url": "https://..."
  }
}
```

### Output

Returns a `.zip` file (`Content-Type: application/zip`) containing:

- `elements.json` — serialized elements array
- `metadata.json` — processing metadata (filename, num_elements, num_pages, etc.)
- `images/` — extracted images (if any)

On success:

```bash
curl -o result.zip -F "file=@document.pdf" http://localhost:8000/extract
unzip -p result.zip elements.json | jq .
```

On error:

```json
{"error": "Processing failed: ValueError"}
```
