#!/usr/bin/env bash
set -euo pipefail

# Attach phase (postAttachCommand): index request, project environment, a complete
# checkout catalog over the staged one, then the attached hooks.
# Spec: agentdev-runtime-images, catalog-lifecycle.

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace="${DEV_WORKSPACE_FOLDER:-$PWD}"
export DEV_WORKSPACE_FOLDER="$workspace"

git config --global gpg.ssh.program ssh-keygen
if command -v codebase-memory-mcp >/dev/null 2>&1; then
  agentdev-runtime cbm index "$workspace"
fi
if [[ -f $workspace/pyproject.toml ]]; then
  agentdev-runtime project sync
fi
if agentdev-runtime catalog complete "$workspace"; then
  agentdev-runtime catalog install "$workspace"
else
  echo "$workspace ships no complete agentdev catalog; keeping the staged catalog."
fi
"$script_dir/run-agentdev-hooks.sh" attached
