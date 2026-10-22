#!/usr/bin/env bash
set -euo pipefail

# SessionStart hook keeping the pin on the pane's conversation: see
# architecture/claude-remote-control-resume. It never fails, so it cannot disturb the session.
id_file="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/remote-control-session-id"

if ! session_id="$(jq -r '.session_id // empty' 2>/dev/null)"; then
  echo "SessionStart input is not JSON; Remote Control pin unchanged." >&2
  exit 0
fi
if [[ -z "$session_id" ]]; then
  echo "SessionStart input has no session_id; Remote Control pin unchanged." >&2
  exit 0
fi

mkdir -p "$(dirname "$id_file")"
tmp_file="$(mktemp "$id_file.XXXXXX")"
printf '%s\n' "$session_id" >"$tmp_file"
mv -f "$tmp_file" "$id_file"
