FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS base
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0 OMP_THREAD_LIMIT=1
WORKDIR /app
# Install linux dependencies
RUN apt-get update && \
    apt-get install -y g++ libmagic-dev poppler-utils tesseract-ocr \
    tesseract-ocr-all libreoffice rustc wget \
    fonts-dejavu fonts-liberation fonts-noto-core fontconfig && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    fc-cache -fv

FROM base AS builder
# Install python dependencies
COPY pyproject.toml uv.lock README.md /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

FROM builder AS runner
ENV PATH="/app/.venv/bin:$PATH"
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
# Pre-download model data so runtime doesn't fetch on first request
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=cache,target=/root/.cache/huggingface \
    echo x > /tmp/preboot.html && soffice --headless --convert-to txt --outdir /tmp /tmp/preboot.html && rm /tmp/preboot.* && \
    uv run --no-sync python -c "from unstructured.nlp.tokenize import _get_nlp; _get_nlp()" && \
    uv run --no-sync python -c "from unstructured.partition.model_init import initialize; initialize()" && \
    uv run --no-sync python -c "from huggingface_hub import hf_hub_download; hf_hub_download('unstructuredio/yolo_x_layout', 'yolox_l0.05.onnx')"
ENV LD_PRELOAD=/lib/x86_64-linux-gnu/libstdc++.so.6
ENV HF_HUB_OFFLINE=1
# Install project
COPY unstructured_api /app/unstructured_api
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev && \
    uv pip uninstall opencv-python
EXPOSE 8000
CMD ["unstructured-api", "--mode", "serverless"]
