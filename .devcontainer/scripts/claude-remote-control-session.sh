#!/usr/bin/env bash
set -euo pipefail

# Pinned-conversation resume and its fallback: see architecture/claude-remote-control-resume.
id_file="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/remote-control-session-id"
remote_control=(--remote-control)
if [[ -n "${1:-}" ]]; then
  remote_control+=("$1")
fi
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
pin_command="$(printf '%q' "$script_dir/claude-remote-control-pin.sh")"
remote_control+=(--settings "$(jq -nc --arg command "$pin_command" \
  '{hooks: {SessionStart: [{hooks: [{type: "command", command: $command}]}]}}')")

stored_id=""
if [[ -r "$id_file" ]]; then
  stored_id="$(<"$id_file")"
fi
if [[ -n "$stored_id" ]] && claude "${remote_control[@]}" --resume "$stored_id"; then
  exit 0
fi

new_id="$(</proc/sys/kernel/random/uuid)"
mkdir -p "$(dirname "$id_file")"
printf '%s\n' "$new_id" >"$id_file"
exec claude "${remote_control[@]}" --session-id "$new_id"
