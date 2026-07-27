#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${ROOT}/.venv-local"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

if [[ ! -x "${VENV}/bin/python" ]]; then
  uv venv "${VENV}" --python 3.13
fi

uv pip install --python "${VENV}/bin/python" --prerelease allow -r "${ROOT}/requirements-ops.txt"
cd "${ROOT}"
exec "${VENV}/bin/python" "$@"