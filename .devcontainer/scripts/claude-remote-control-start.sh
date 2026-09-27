#!/usr/bin/env bash
set -euo pipefail

if [[ "${AGENTDEV_CLAUDE_AUTOSTART:-}" != "1" ]]; then
  exit 0
fi

if [[ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]]; then
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

# Add only the variable name to tmux's client-environment allowlist. The value
# is inherited by the new session without appearing in argv, logs, or files.
if ! tmux_error="$(tmux start-server \; \
  set-option -gqsa update-environment " CLAUDE_CODE_OAUTH_TOKEN" \; \
  new-session -d -s "$session" -c "$workspace" "exec claude /remote-control" 2>&1)"; then
  if tmux has-session -t "=$session" 2>/dev/null; then
    echo "Claude Remote Control tmux session '$session' is already running."
    exit 0
  fi
  printf 'Failed to start Claude Remote Control: %s\n' "$tmux_error" >&2
  exit 1
fi

echo "Started Claude Remote Control in tmux session '$session'."
