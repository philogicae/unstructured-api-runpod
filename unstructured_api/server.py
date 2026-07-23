import logging
from base64 import b64encode
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from unstructured_api.process.document import parse_document
from unstructured_api.process.utils import exceeds_size, get_filename
from unstructured_api.settings import MIDDLEWARE_PARAMS, SUPPORTED_FORMATS

logger = logging.getLogger(__name__)

app = FastAPI(title="Unstructured API")
app.add_middleware(
    CORSMiddleware,
    **MIDDLEWARE_PARAMS,
)


@app.get("/")
async def root():
    return {"status": "ok"}


@app.get("/formats")
async def formats():
    return SUPPORTED_FORMATS


@app.post("/extract")
async def extract(
    file: UploadFile | None = File(None),  # noqa: B008
    file_base64: str | None = Form(None),
    file_url: str | None = Form(None),
):
    if file and file.filename:
        content = await file.read()
        if exceeds_size(content):
            logger.warning("Upload rejected: %s exceeds max size", file.filename)
            raise HTTPException(status_code=413, detail="File exceeds max upload size")
        file_base64 = b64encode(content).decode("utf-8")
    elif file_base64 and exceeds_size(file_base64):
        logger.warning("Base64 upload rejected: exceeds max size")
        raise HTTPException(
            status_code=413, detail="Base64 content exceeds max upload size"
        )
    filename = get_filename(filename=file.filename if file else None, file_url=file_url)
    logger.info("Extracting document: filename=%s", filename)
    result = parse_document(
        file_content=file_base64,
        file_url=file_url,
        filename=filename,
    )
    if isinstance(result, dict):
        return result
    zip_name = f"{Path(filename).stem}.zip" if filename else "extracted.zip"
    return Response(
        content=result,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )


def start(host: str = "0.0.0.0", port: int = 8000):
    uvicorn.run(app, host=host, port=port, log_level="info")
