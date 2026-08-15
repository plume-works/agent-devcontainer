#!/usr/bin/env bash
#
# Verify Python style compliance with ruff (the CI gate).
#
# The pre-commit hooks (locally) and Super-Linter (in CI) apply ruff's formatter
# and autofixes; this script is the non-mutating check, so it is safe to run
# anywhere and needs no Docker.
#
# ruff runs through `uv run` when the target repository is a uv project, so the
# version matches the pinned one; otherwise it falls back to ruff on PATH.
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

# Prefer the project environment via `uv run`, so the ruff version matches the
# pinned one. uv resolves the project from the working directory, so point it at
# $root_dir explicitly -- the targets may be anywhere.
#
# This script ships in the portable `agentdev` plugin and must still work in a
# repository that is not a uv project. Fall back in order: the project
# environment, then a uv-provided ruff, then whatever ruff is on PATH.
# shellcheck disable=SC2154 # root_dir is exported by __utils.sh
if command -v uv >/dev/null 2>&1 && [ -f "$root_dir/pyproject.toml" ]; then
  ruff=(uv run --project "$root_dir" ruff)
elif command -v ruff >/dev/null 2>&1; then
  ruff=(ruff)
elif command -v uv >/dev/null 2>&1; then
  ruff=(uv tool run ruff)
else
  echo "ruff not found: install uv or ruff, or invoke via 'uv run'." >&2
  exit 1
fi

"${ruff[@]}" format --check --quiet "${targets[@]}"
"${ruff[@]}" check --quiet "${targets[@]}"
