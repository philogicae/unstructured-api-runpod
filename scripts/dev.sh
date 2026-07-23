#!/bin/bash
set -e

# Lock and sync dependencies
uv lock && uv sync -U --link-mode=copy

# Format code
uv run ruff format

# Check for linting errors
uv run ruff check --fix

# Run type checking
uv run ty check

# Run tests with coverage
uv run pytest --cov=unstructured_api --cov-report=term-missing