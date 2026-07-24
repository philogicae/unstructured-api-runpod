import io
import json
import logging
import time
import urllib.request
from base64 import b64decode
from os import getenv
from pathlib import Path
from shutil import rmtree
from zipfile import ZipFile

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

RUNPOD_ENDPOINT_ID = getenv("RUNPOD_ENDPOINT_ID")
RUNPOD_API_KEY = getenv("RUNPOD_API_KEY")
if not RUNPOD_ENDPOINT_ID or not RUNPOD_API_KEY:
    raise RuntimeError("RUNPOD_ENDPOINT_ID and RUNPOD_API_KEY must be set in .env")
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {RUNPOD_API_KEY}",
}
API_BASE = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}"
TEST_DATA = {
    "input": {
        "file_url": "https://raw.githubusercontent.com/Unstructured-IO/unstructured/refs/heads/main/example-docs/pdf/embedded-images-tables.pdf"
    }
}


def _request(url: str, *, data: bytes | None = None, timeout: int = 30) -> dict:
    req = urllib.request.Request(  # noqa: S310
        url, data=data, headers=HEADERS, method="POST" if data else "GET"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _complete(result: dict) -> bool:
    return result.get("status") == "COMPLETED" and "error" not in result


def _poll(job_id: str) -> dict:
    while True:
        time.sleep(2)
        result = _request(f"{API_BASE}/status/{job_id}")
        logger.info("Status: %s", result.get("status"))
        if _complete(result) or result.get("status") in ("FAILED", "CANCELLED"):
            return result


def _extract_zip(output: dict) -> None:
    zip_bytes = b64decode(output["zip"])
    out_dir = Path(__file__).parent / "zip"
    if out_dir.exists():
        rmtree(out_dir)
    out_dir.mkdir()
    with ZipFile(io.BytesIO(zip_bytes)) as zf:
        zf.extractall(out_dir)
    logger.info("Extracted %d bytes to %s", len(zip_bytes), out_dir)


def runsync(data: dict) -> dict | None:
    logger.info("Sending runsync request to endpoint %s", RUNPOD_ENDPOINT_ID)
    result = _request(
        f"{API_BASE}/runsync",
        data=json.dumps(data).encode("utf-8"),
        timeout=600,
    )

    job_id = result.get("id")
    if not _complete(result) and job_id:
        logger.info("Status: %s — polling /status/%s", result.get("status"), job_id)
        result = _poll(job_id)

    output = result.get("output")
    if not _complete(result) or not isinstance(output, dict) or "error" in output:
        if isinstance(output, dict):
            logger.info("Total time: %s seconds", output.get("total_time"))
        logger.error("Request failed: %s", json.dumps(result, indent=2))
        return None

    logger.info("Total time: %s seconds", output.get("total_time"))
    _extract_zip(output)
    return result


if __name__ == "__main__":
    runsync(TEST_DATA)
