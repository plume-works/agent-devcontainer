#!/usr/bin/env bash
set -euo pipefail

# Shares OpenCode's auth.json across worktrees via the agentdev-agents-auth volume; OpenCode
# rewrites it in place, so the link survives login, logout, and refresh.
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
