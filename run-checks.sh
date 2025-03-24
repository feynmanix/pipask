#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

echo -e "\n== Running pytest (tests) =="
poetry run pytest .

echo -e "\n== Running pyright (type check) =="
poetry run pyright .

echo -e "\n== Running ruff check (linter) =="
poetry run ruff check .

echo -e "\n== Running ruff format (code formatter) =="
poetry run ruff format .

echo -e "\n== Running bandit (static analyzer) =="
poetry run bandit -c pyproject.toml -r .
