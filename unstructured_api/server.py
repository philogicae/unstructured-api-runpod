from base64 import b64encode

from fastapi import FastAPI, File, Form, UploadFile

from unstructured_api.process.document import parse_document
from unstructured_api.schema import get_schema_server
from unstructured_api.settings import SUPPORTED_FORMATS

app = FastAPI(title="Unstructured API")


@app.get("/")
async def health():
    return {"status": "ok"}


@app.get("/schema")
async def schema():
    return {"schema": get_schema_server()}


@app.get("/formats")
async def formats():
    return SUPPORTED_FORMATS


@app.post("/parse")
async def parse(
    file: UploadFile | None = File(None),
    file_base64: str | None = Form(None),
    file_url: str | None = Form(None),
):
    if file and file.filename:
        content = await file.read()
        file_base64 = b64encode(content).decode("utf-8")
        filename = file.filename
    else:
        filename = None

    return parse_document(
        file_content=file_base64,
        file_url=file_url,
        filename=filename,
    )


def start(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="info")
