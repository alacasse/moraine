#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
export UV_CACHE_DIR="$PWD/.uv-cache"
export UV_PYTHON_INSTALL_DIR="$PWD/.python"
uv venv --python python3 .venv
uv pip sync --python .venv/bin/python --require-hashes --only-binary :all: requirements.lock
