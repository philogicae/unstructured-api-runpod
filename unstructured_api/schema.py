def get_schema_server():
    return {
        "/health": "GET — health check",
        "/schema": "GET — return API schema",
        "/formats": "GET — return supported file formats",
        "/parse": "POST — parse document (multipart or JSON)",
    }


def get_schema_serverless():
    return {
        "input": {
            "file_base64": "str (base64-encoded file content)",
            "file_url": "str (public URL to download)",
            "filename": "str (hint for file extension)",
        },
        "output": {
            "elements": [
                {
                    "type": "str",
                    "text": "str",
                    "metadata": {"page_number": "int", "filename": "str"},
                }
            ],
            "metadata": {
                "filename": "str",
                "num_elements": "int",
                "processing_time": "float",
            },
            "error": "str | null",
        },
    }
