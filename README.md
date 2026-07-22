# unstructured-api

Document parsing/OCR API powered by [unstructured](https://github.com/Unstructured-IO/unstructured). Supports PDF, DOCX, PPTX, images, HTML, EPUB, and [many more](https://docs.unstructured.io/open-source/introduction/supported-file-types).

Runs as a [**RunPod serverless endpoint**](https://www.runpod.io/) or a **standalone FastAPI server**.

## Quick start

```bash
./scripts/dev.sh
uv run unstructured-api --mode api    # start FastAPI on :8000
```

## Docker

```bash
docker compose up -d
curl -X POST http://localhost:8000/parse -F "file=@document.pdf"
```

Deployment is handled via CI — tag a commit and push. See `.github/workflows/ci-cd.yml`.

## API

### POST /parse

Upload a file directly (multipart) or pass base64/URL (JSON):

| Field         | Type       | Description                             |
| ------------- | ---------- | --------------------------------------- |
| `file`        | UploadFile | Attach a file directly (multipart only) |
| `file_base64` | str        | Base64-encoded file content             |
| `file_url`    | str        | Public URL to download                  |
| `filename`    | str        | Hint for file extension detection       |

Uses `hi_res` strategy with auto-detected OCR languages.

### GET /formats

Returns all supported file formats categorized by type.

### Serverless (RunPod)

```json
{
  "input": {
    "file_base64": "<base64>",
    "file_url": "https://...",
    "filename": "document.pdf"
  }
}
```

### Output

```json
{
  "elements": [
    {
      "type": "Title",
      "text": "Introduction",
      "metadata": {
        "page_number": 1,
        "filename": "doc.pdf",
        "filetype": "application/pdf",
        "image_path": null,
        "text_as_html": null,
        "languages": ["eng"]
      }
    }
  ],
  "metadata": {
    "filename": "doc.pdf",
    "file_size": 123456,
    "num_elements": 42,
    "num_pages": 3,
    "processing_time": 1.23
  },
  "error": null
}
```
