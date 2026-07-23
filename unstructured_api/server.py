import logging
from base64 import b64encode
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from unstructured_api.process.document import parse_document
from unstructured_api.schema import get_schema_server
from unstructured_api.settings import CORS_ORIGINS, MAX_UPLOAD_SIZE, SUPPORTED_FORMATS

logger = logging.getLogger(__name__)

app = FastAPI(title="Unstructured API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def health():
    return {"status": "ok"}


@app.get("/schema")
async def schema():
    return {"schema": get_schema_server()}


@app.get("/formats")
async def formats():
    return SUPPORTED_FORMATS


@app.post("/extract")
async def extract(
    file: UploadFile | None = File(None),
    file_base64: str | None = Form(None),
    file_url: str | None = Form(None),
):
    log_filename = None
    if file and file.filename:
        content = await file.read()
        if len(content) > MAX_UPLOAD_SIZE:
            logger.warning("Upload rejected: %s exceeds max size", file.filename)
            raise HTTPException(status_code=413, detail="File exceeds max upload size")
        file_base64 = b64encode(content).decode("utf-8")
        log_filename = file.filename
    elif file_base64 and len(file_base64) > MAX_UPLOAD_SIZE * 4 // 3:
        logger.warning("Base64 upload rejected: exceeds max size")
        raise HTTPException(
            status_code=413, detail="Base64 content exceeds max upload size"
        )

    logger.info("Extracting document: filename=%s", log_filename)
    result = parse_document(
        file_content=file_base64,
        file_url=file_url,
        filename=log_filename,
    )

    if isinstance(result, dict):
        return result

    zip_name = f"{Path(log_filename).stem}.zip" if log_filename else "extracted.zip"
    return Response(
        content=result,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )


def start(host: str = "0.0.0.0", port: int = 8000):
    uvicorn.run(app, host=host, port=port, log_level="info")
