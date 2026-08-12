#!/usr/bin/env bash
# This script is run after the container is started, but before the VSCode extension host is started.
# This allows to avoid race conditions and setup safe environment for the extension host to run in.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$script_dir/codebase-memory-mcp-start.sh"

"$script_dir/setup-pre-commit.sh"
"$script_dir/setup-keyring.sh"
"$script_dir/firewall.sh"
/start-xpra.sh --background
"$script_dir/configure-codex.py"

# Repairs the shared auth.json symlink if a `codex logout` during this container's
# previous run destroyed it; see link-codex-auth.sh for why that can happen.
"$script_dir/link-codex-auth.sh"
