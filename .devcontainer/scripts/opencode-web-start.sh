#!/usr/bin/env bash
# Starts the OpenCode web UI from the Coder agent start; see spec/opencode-web.
set -euo pipefail

for command in opencode tmux; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "$command is not installed; skipping OpenCode web startup." >&2
    exit 0
  fi
done

session="opencode"
workspace="${DEV_WORKSPACE_FOLDER:-$PWD}"

# The web UI opens a directory at /<base64url, unpadded>/session; Coder's agent
# sets VSCODE_PROXY_URI to its port-URL template.
local_url_template="http://127.0.0.1:{{port}}"
base_url="${VSCODE_PROXY_URI:-$local_url_template}"
base_url="${base_url//\{\{port\}\}/4096}"
encoded="$(printf '%s' "$workspace" | base64 | tr -d '\n=' | tr '+/' '-_')"
link="${base_url%/}/$encoded/session"

# Listening beyond localhost requires the server password OpenCode enforces.
hostname="127.0.0.1"
if [[ -n "${OPENCODE_SERVER_PASSWORD:-}" ]]; then
  hostname="0.0.0.0"
fi

if tmux -L "$session" has-session -t "=$session" 2>/dev/null; then
  echo "OpenCode web tmux session '$session' is already running: $link"
  exit 0
fi

# Without DISPLAY, `opencode web` cannot open a browser on the Xpra desktop.
pane_command="exec env -u DISPLAY opencode web --port 4096 --hostname $hostname"
tmux_start=(tmux -L "$session" start-server \; new-session -d -s "$session" -c "$workspace" \
  "$pane_command")

if ! tmux_error="$("${tmux_start[@]}" 2>&1)"; then
  if tmux -L "$session" has-session -t "=$session" 2>/dev/null; then
    echo "OpenCode web tmux session '$session' is already running: $link"
    exit 0
  fi
  printf 'Failed to start OpenCode web: %s\n' "$tmux_error" >&2
  exit 1
fi

echo "Started OpenCode web in tmux session '$session' on $hostname:4096: $link"
