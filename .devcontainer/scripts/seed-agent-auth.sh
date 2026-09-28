#!/usr/bin/env bash
set -euo pipefail

seed_credential() {
    local env_name="$1"
    local target="$2"
    local label="$3"
    local value="${!env_name:-}"
    local lock_fd
    local temp

    [[ -n "$value" ]] || return 0
    mkdir -p "$(dirname "$target")"
    chmod 700 "$(dirname "$target")"

    exec {lock_fd}>"${target}.seed.lock"
    chmod 600 "${target}.seed.lock"
    flock "$lock_fd"
    if [[ -s "$target" ]]; then
        chmod 600 "$target"
        return 0
    fi

    temp="$(mktemp "${target}.seed.XXXXXX")"
    chmod 600 "$temp"
    if ! printf '%s' "$value" | python3 -c '
import json
import sys

value = json.load(sys.stdin)
if not isinstance(value, dict):
    raise SystemExit("credential must be a JSON object")
json.dump(value, sys.stdout, separators=(",", ":"))
' >"$temp"; then
        rm -f "$temp"
        echo "Invalid JSON in $env_name; $label credentials were not seeded." >&2
        return 1
    fi

    mv -f "$temp" "$target"
    chmod 600 "$target"
    echo "Seeded $label credentials."
}

seed_credential \
    AGENTDEV_CLAUDE_JSON \
    "${AGENTDEV_CLAUDE_AUTH_PATH:-/root/.agents-auth/claude/.credentials.json}" \
    Claude
seed_credential \
    AGENTDEV_CODEX_JSON \
    "${AGENTDEV_CODEX_AUTH_PATH:-/root/.agents-auth/codex/auth.json}" \
    Codex
