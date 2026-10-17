#!/usr/bin/env bash
set -euo pipefail

# Shares OpenCode's provider logins across worktrees: auth.json lives in the shared
# agentdev-agents-auth volume and is symlinked into OpenCode's per-instance data directory.
# OpenCode rewrites auth.json in place, so the link survives login, logout, and refresh.
# See architecture/agent-auth-persistence.

opencode_auth_dir="${AGENTDEV_AGENTS_AUTH_DIR:-/root/.agents-auth}/opencode"
opencode_auth_target="$opencode_auth_dir/auth.json"
opencode_auth_local="${XDG_DATA_HOME:-$HOME/.local/share}/opencode/auth.json"

mkdir -p "$opencode_auth_dir" "$(dirname "$opencode_auth_local")"
chmod 700 "$opencode_auth_dir"

if [[ -f "$opencode_auth_local" && ! -L "$opencode_auth_local" ]]; then
    mv "$opencode_auth_local" "$opencode_auth_target"
    chmod 600 "$opencode_auth_target"
fi

# The target need not exist: OpenCode's first login creates it through the link.
ln -sfn "$opencode_auth_target" "$opencode_auth_local"
