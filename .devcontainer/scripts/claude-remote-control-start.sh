#!/usr/bin/env bash
set -euo pipefail

if [[ "${AGENTDEV_CLAUDE_AUTOSTART:-}" != "1" ]]; then
  exit 0
fi

credential_file="${AGENTDEV_CLAUDE_AUTH_PATH:-${CLAUDE_SECURESTORAGE_CONFIG_DIR:-$HOME/.claude}/.credentials.json}"
file_auth=false
if [[ -s "$credential_file" ]]; then
  file_auth=true
elif [[ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]]; then
  echo "AGENTDEV_CLAUDE_AUTOSTART=1 but Claude auth is unavailable; skipping Remote Control."
  exit 0
fi

for command in claude tmux; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "$command is not installed; skipping Claude Remote Control startup." >&2
    exit 0
  fi
done

session="claude-remote"
workspace="${DEV_WORKSPACE_FOLDER:-$PWD}"

if tmux has-session -t "=$session" 2>/dev/null; then
  echo "Claude Remote Control tmux session '$session' is already running."
  exit 0
fi

# A full login file takes priority because setup tokens cannot establish Remote
# Control sessions. Keep the setup token out of that Claude process.
if [[ "$file_auth" == true ]]; then
  tmux_start=(tmux start-server \; new-session -d -s "$session" -c "$workspace" \
    "exec env -u CLAUDE_CODE_OAUTH_TOKEN claude /remote-control")
else
  # Add only the variable name to tmux's client-environment allowlist.
  tmux_start=(tmux start-server \; \
    set-option -gqsa update-environment " CLAUDE_CODE_OAUTH_TOKEN" \; \
    new-session -d -s "$session" -c "$workspace" "exec claude /remote-control")
fi

if ! tmux_error="$("${tmux_start[@]}" 2>&1)"; then
  if tmux has-session -t "=$session" 2>/dev/null; then
    echo "Claude Remote Control tmux session '$session' is already running."
    exit 0
  fi
  printf 'Failed to start Claude Remote Control: %s\n' "$tmux_error" >&2
  exit 1
fi

echo "Started Claude Remote Control in tmux session '$session'."
