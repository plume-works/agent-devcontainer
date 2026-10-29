#!/usr/bin/env bash
set -euo pipefail

# Attach phase (postAttachCommand): index request, project environment, a complete
# checkout catalog over the staged one, then the attached hooks.
# Spec: agentdev-runtime-images, catalog-lifecycle.

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=runtime-paths.sh
source "$script_dir/runtime-paths.sh"
workspace="${DEV_WORKSPACE_FOLDER:-$PWD}"
export DEV_WORKSPACE_FOLDER="$workspace"

git config --global gpg.ssh.program ssh-keygen
"$script_dir/codebase-memory-mcp-index.sh"
if [[ -f $workspace/pyproject.toml ]]; then
  "$script_dir/uv-sync.sh"
fi
if agentdev_complete_catalog "$workspace"; then
  "$script_dir/setup-agent-state.sh" catalog "$workspace"
else
  echo "$workspace ships no complete agentdev catalog; keeping the staged catalog."
fi
"$script_dir/run-agentdev-hooks.sh" attached
