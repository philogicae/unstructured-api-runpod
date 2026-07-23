import logging
from base64 import b64encode
from time import time as now
from typing import Any, cast

from runpod import serverless
from runpod.serverless.utils import rp_cleanup, rp_debugger
from runpod.serverless.utils.rp_validator import validate

from unstructured_api.process.document import parse_document
from unstructured_api.process.utils import elapsed, exceeds_size, get_filename

logger = logging.getLogger(__name__)

INPUT_SCHEMA = {
    "file_base64": {"type": str, "required": False, "default": None},
    "file_url": {"type": str, "required": False, "default": None},
}


@rp_debugger.FunctionTimer
def handler(job):
    logger.info("Start job")
    started = now()
    job_input = job["input"]
    validated = validate(job_input, INPUT_SCHEMA)
    if "errors" in validated:
        logger.warning("Validation failed: %s", validated["errors"])
        return {"error": validated["errors"], "total_time": elapsed(started)}
    inp = cast(dict[str, Any], validated["validated_input"])
    file_content = inp.get("file_base64")
    file_url = inp.get("file_url")
    if file_content and exceeds_size(file_content):
        logger.warning("Base64 input rejected: exceeds max size")
        return {
            "error": "File exceeds max upload size",
            "total_time": elapsed(started),
        }
    filename = get_filename(file_url=file_url)
    logger.info("Processing job: filename=%s", filename)
    try:
        result = parse_document(
            file_content=file_content,
            file_url=file_url,
            filename=filename,
        )
        if isinstance(result, dict):
            return result | {"total_time": elapsed(started)}
        return {"zip": b64encode(result).decode("utf-8")} | {
            "total_time": elapsed(started)
        }
    finally:
        rp_cleanup.clean()


def start():
    serverless.start({"handler": handler})
