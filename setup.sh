#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
venv_python="$repo_root/.venv/bin/python"
if [[ ! -x "$venv_python" ]]; then
  command -v python3.12 >/dev/null || { echo "Python 3.12 is required." >&2; exit 1; }
  python3.12 -m venv "$repo_root/.venv"
fi
"$venv_python" -m pip install --upgrade pip
"$venv_python" -m pip install --requirement "$repo_root/requirements.lock"
"$venv_python" -m pip install --editable "$repo_root"
"$venv_python" -m wpi_sensitivity --self-test
echo "Setup complete. Excel analyses require Windows with desktop Excel."
