#!/usr/bin/env bash
set -xeuo pipefail

root_dir="${DEV_WORKSPACE_FOLDER:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

cd "$root_dir"

# A caller that never commits — the CI responder job — can opt out: installing
# the hooks eagerly builds a virtualenv per hook, which costs minutes for hooks
# such a job never fires. Unset (the devcontainer default) installs as before.
if [[ -n "${AGENTDEV_SKIP_PRE_COMMIT:-}" ]]; then
    echo "AGENTDEV_SKIP_PRE_COMMIT is set; skipping pre-commit hook installation."
    exit 0
fi

command -v pre-commit || echo "pre-commit not found"

# Install the repository's hooks for this checkout. Re-running this command is
# safe and ensures both staged-file and pre-push checks are available.
pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push || echo "pre-commit install failed. log: $(cat "$HOME/.cache/pre-commit/pre-commit.log")"
