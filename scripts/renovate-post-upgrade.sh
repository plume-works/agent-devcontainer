#!/usr/bin/env bash
# Renovate's one post-upgrade task: see architecture/renovate-post-upgrade.

set -euo pipefail

# renovate: datasource=npm depName=@devcontainers/cli
DEVCONTAINER_CLI_VERSION="0.89.0"

cd "$(git rev-parse --show-toplevel)"

# Renovate's edits are uncommitted in its clone, so the diff against HEAD is the bump.
changed_files()
{
  git diff --name-only --diff-filter=d HEAD
  git ls-files --others --exclude-standard
}

mapfile -t changed < <(changed_files)
if [[ ${#changed[@]} -eq 0 ]]; then
  exit 0
fi

uv run --frozen scripts/refresh-pin-checksums.py "${changed[@]}"

if printf '%s\n' "${changed[@]}" | grep -qx '.devcontainer/devcontainer.json'; then
  bunx --package "@devcontainers/cli@${DEVCONTAINER_CLI_VERSION}" \
    devcontainer upgrade --workspace-folder .
fi

# pre-commit through uv, not the image's apt copy: see architecture/renovate-post-upgrade.
mapfile -t changed < <(changed_files)
if ! uv run --frozen pre-commit run --files "${changed[@]}"; then
  mapfile -t changed < <(changed_files)
  uv run --frozen pre-commit run --files "${changed[@]}"
fi
