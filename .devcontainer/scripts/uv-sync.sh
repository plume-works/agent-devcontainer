#!/usr/bin/env bash
set -euo pipefail

workspace="${DEV_WORKSPACE_FOLDER:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

cd "$workspace"

# UV_PROJECT_ENVIRONMENT keeps the environment on the /uv volume, which is the
# same filesystem as UV_CACHE_DIR. That is what lets uv hardlink packages out of
# its cache instead of copying them; an in-tree .venv would sit on the host bind
# mount and silently fall back to copying. Commands reach it through `uv run`.

# Migration: shed the .venv symlink earlier revisions created, so existing
# containers drop it on the next postAttach without a rebuild. Removable once
# every active worktree has re-synced.
#
# Only ever remove a link this repository created. Earlier revisions ran
# `ln -s "$UV_PROJECT_ENVIRONMENT" .venv`, so the target is always under
# /uv/venvs/ -- match that prefix rather than the current
# UV_PROJECT_ENVIRONMENT, since the stale links predate the path change and
# still carry the old per-workspace basename. Anything else is someone's
# deliberate link and is left alone, as is a real .venv directory (-L).
venv_link_prefix=/uv/venvs/
if [ -L "$workspace/.venv" ]; then
    venv_target=$(readlink "$workspace/.venv")
    case "$venv_target" in
        "$venv_link_prefix"*) rm "$workspace/.venv" ;;
        *) echo "uv-sync: leaving .venv -> $venv_target (not a managed link)" >&2 ;;
    esac
fi

uv sync --all-groups --all-extras
