#!/bin/bash
set -e

uv run unstructured-api --test_input '{"input": {"file_url": "https://raw.githubusercontent.com/Unstructured-IO/unstructured/refs/heads/main/example-docs/pdf/embedded-images-tables.pdf"}}'
