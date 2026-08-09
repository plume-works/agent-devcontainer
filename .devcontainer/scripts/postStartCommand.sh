#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$script_dir/setup-pre-commit.sh"
"$script_dir/setup-keyring.sh"
"$script_dir/firewall.sh"
/start-xpra.sh --background
"$script_dir/configure-codex.py"

# Repairs the shared auth.json symlink if a `codex logout` during this container's
# previous run destroyed it; see link-codex-auth.sh for why that can happen.
"$script_dir/link-codex-auth.sh"

# Re-register this checkout's catalog over whatever postCreateCommand.sh installed
# from the image, so the workspace copy is the one agents load. A no-op in a
# project that ships no marketplace of its own.
"$script_dir/reinstall-agentdev-codex.sh"
"$script_dir/reinstall-agentdev-claude.sh"
