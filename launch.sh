#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
venv_python="$repo_root/.venv/bin/python"
[[ -x "$venv_python" ]] || { echo "Environment not found. Run ./setup.sh first." >&2; exit 1; }
cd "$repo_root"
exec "$venv_python" -m wpi_sensitivity "$@"
