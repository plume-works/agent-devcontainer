#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Refresh the workspace catalog on every editor attachment so newly added agents
# and skills are copied into both clients' plugin caches after a window reload.
"$script_dir/reinstall-agentdev-codex.sh"
"$script_dir/reinstall-agentdev-claude.sh"
