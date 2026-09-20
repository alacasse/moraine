#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
.tools/opa check --strict src/moraine_email/policy
.tools/opa test src/moraine_email/policy -v
.venv/bin/python -m pytest "$@"
