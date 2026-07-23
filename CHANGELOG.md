## [1.0.0] - 2026-07-23

### 🚀 Features

- Feat: zip-based output, image dedup, security hardening, CORS, logging, and RunPod deployment

API changes:

- Replace raw JSON response with application/zip containing elements.json,
  metadata.json, and images/ directory
- Rename POST /parse → POST /extract
- Remove filename from form fields (inferred from file suffix)
- Add CORS middleware with configurable origins (default: \*)
- Add 200 MB size limits on both upload (multipart/base64) and URL downloads
- Raise HTTP 413 on oversized uploads

Image processing:

- Add perceptual hash dedup (PHash via imagededup) to filter duplicate images
- Convert Table elements to Image type; downgrade duplicate tables to Text
  with text_as_html content
- Drop small icon images below MIN_IMAGE_PIXELS threshold
- Lowercase text in clean_text for consistent output

Security:

- SSRF protection: reject non-http(s) URL schemes in url_to_tempfile
- Fix file descriptor / temp file leak when urlopen fails
- Guard against malformed Content-Length header in URL downloads
- Sanitize internal temp paths from error messages returned to client

Infrastructure:

- Add structured logging (logger) throughout all modules
- Lazy-init Magika singleton to avoid import-time overhead
- Add git-cliff changelog config (cliff.toml)
- Add MIT LICENSE
- Add RunPod hub.json and tests.json for serverless deployment
- Simplify CI/CD: drop build + PyPI publish steps, add coverage reporting
- Rename Docker Hub image to unstructured-api-runpod
- Add libreoffice and rustc to CI/Docker deps; switch CI to Dockerfile
- Add healthcheck to compose.yml
- Comprehensive .dockerignore and .gitignore

Dependencies:

- Add imagededup, opencv-contrib-python, pytest-cov
- Drop paddleocr from extras
- Pin all deps with minimum versions
- Build imagededup from source (no-binary)

Testing:

- Comprehensive test suite: document, server, utils, main, worker modules
- Tests for zip output parsing, image size checks, URL download with local
  HTTP server, SSRF rejection, oversized uploads, CORS headers, CLI args
- Coverage reporting in CI with pytest-cov

Other:

- Update README with new API docs, deploy instructions, badges
- Version bump 1.0.0 → 0.9.0
- Update repo URL to philogicae/unstructured-api-runpod
- Add comment annotations throughout Dockerfiles
- Refactor **main**.py imports for clarity

### 💼 Changes

- Init

### 🧪 Testing

- Test: add parallel execution, timeouts, mocking, and lazy imports

### ⚙️ Miscellaneous Tasks

- Chore: bump version 0.9.0 → 1.0.0
- Chore: update changelog
