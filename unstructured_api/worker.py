import logging
from typing import Any, cast

from runpod import serverless
from runpod.serverless.utils import rp_cleanup
from runpod.serverless.utils.rp_validator import validate

from unstructured_api.process.document import parse_document
from unstructured_api.schema import get_schema_serverless

logger = logging.getLogger(__name__)

INPUT_SCHEMA = {
    "file_base64": {"type": str, "required": False, "default": None},
    "file_url": {"type": str, "required": False, "default": None},
}


def handler(job):
    job_input = job["input"]
    if job_input.get("schema"):
        return {"schema": get_schema_serverless()}

    validated = validate(job_input, INPUT_SCHEMA)
    if "errors" in validated:
        logger.warning("Validation failed: %s", validated["errors"])
        return {"error": validated["errors"]}

    inp = cast(dict[str, Any], validated["validated_input"])
    logger.info("Processing job")

    try:
        return parse_document(
            file_content=inp["file_base64"],
            file_url=inp["file_url"],
        )
    finally:
        rp_cleanup.clean()


def start():
    serverless.start({"handler": handler})
