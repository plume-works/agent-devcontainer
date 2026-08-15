#!/usr/bin/env bash
set -euo pipefail

workspace="${DEV_WORKSPACE_FOLDER:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

cd "$workspace"

# UV_PROJECT_ENVIRONMENT points at a named volume so the environment survives
# container rebuilds. BREAKING CHANGE: this script no longer creates a .venv
# symlink at the workspace root — invoke project tools through `uv run` instead
# of activating an environment. A symlink left by an older worktree is removed
# so it cannot point at an environment that is no longer synced; a real .venv
# directory is left alone, since a consuming project may legitimately own one.
if [ -L "$workspace/.venv" ]; then
    rm -f "$workspace/.venv"
fi

uv sync --all-groups --all-extras
