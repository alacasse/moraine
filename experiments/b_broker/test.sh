#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
export UV_CACHE_DIR="$PWD/.cache/uv"
export UV_PYTHON_DOWNLOADS=never
export UV_PROJECT_ENVIRONMENT="$PWD/.venv"
python3 bootstrap.py
uv sync --frozen --quiet
.tools/opa-1.9.0/opa check --strict policy
.tools/opa-1.9.0/opa test policy -v
.venv/bin/python -m pytest -q "$@"
