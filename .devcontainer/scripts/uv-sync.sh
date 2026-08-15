#!/usr/bin/env bash
set -euo pipefail

workspace="${DEV_WORKSPACE_FOLDER:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

cd "$workspace"

# UV_PROJECT_ENVIRONMENT keeps the environment on the /uv volume, which is the
# same filesystem as UV_CACHE_DIR. That is what lets uv hardlink packages out of
# its cache instead of copying them; an in-tree .venv would sit on the host bind
# mount and silently fall back to copying. Commands reach it through `uv run`.

# Migration: shed the .venv symlink earlier revisions created, so existing
# containers drop it on the next postAttach without a rebuild. Guarded on -L and
# using a plain rm so a real host-created .venv directory is never touched.
# Removable once every active worktree has re-synced.
if [ -L "$workspace/.venv" ]; then
    rm "$workspace/.venv"
fi

uv sync --all-groups --all-extras
