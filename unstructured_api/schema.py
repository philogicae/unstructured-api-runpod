def get_schema_server():
    return {
        "/health": "GET — health check",
        "/schema": "GET — return this API schema",
        "/formats": "GET — return supported file formats grouped by type (documents, images, text)",
        "/extract": {
            "method": "POST",
            "description": "Upload a document and extract structured elements. Returns application/zip with elements.json, metadata.json, and images/.",
            "input": {
                "file": "UploadFile (multipart) — attach a file directly",
                "file_base64": "str (form field) — base64-encoded file content",
                "file_url": "str (form field) — public URL to download the file from",
            },
            "output": {
                "success": "application/zip (elements.json, metadata.json, images/)",
                "error": 'application/json — {"error": "<reason>"}',
            },
        },
    }


def get_schema_serverless():
    return {
        "input": {
            "file_base64": "str (base64-encoded file content)",
            "file_url": "str (public URL to download)",
        },
        "output": {
            "success": "application/zip binary (elements.json, metadata.json, images/)",
            "error": '{"error": "<reason>"}',
        },
    }
