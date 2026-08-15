#!/usr/bin/env bash
#
# Verify Python style compliance with ruff (the CI gate).
#
# The pre-commit hooks (locally) and Super-Linter (in CI) apply ruff's formatter
# and autofixes; this script is the non-mutating check, so it is safe to run
# anywhere and needs no Docker.
#
# ruff is resolved through `uv run --no-sync` when the tree is a uv project, and
# otherwise from an in-tree .venv or PATH. Nothing here installs or upgrades
# packages.
#
# Usage:
#   python-lint-check.sh [PATH ...]
#
# With no arguments this checks the whole repository (ruff honors .gitignore and
# its own default excludes). Pass explicit
# paths (files or directories) to scope the check for rapid iteration.
#
# Exits non-zero when ruff reports any violation.

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=/dev/null
source "$script_dir/__utils.sh"

if [ "$#" -gt 0 ]; then
  targets=("$@")
else
  # shellcheck disable=SC2154 # exported by __utils.sh
  targets=("$root_dir")
fi

# Resolve ruff at the pinned version without mutating the environment: prefer the
# uv project runner (--no-sync keeps this a check, never an install), then an
# in-tree .venv for projects that own one, then whatever ruff is on PATH.
# shellcheck disable=SC2154 # root_dir is exported by __utils.sh
if uv run --no-sync --project "$root_dir" ruff --version >/dev/null 2>&1; then
  ruff() { uv run --no-sync --project "$root_dir" ruff "$@"; }
elif [ -x "$root_dir/.venv/bin/ruff" ]; then
  ruff() { "$root_dir/.venv/bin/ruff" "$@"; }
elif ! command -v ruff >/dev/null 2>&1; then
  echo "ruff not found: run 'uv sync', or invoke via 'uv run'." >&2
  exit 1
fi

ruff format --check --quiet "${targets[@]}"
ruff check --quiet "${targets[@]}"
