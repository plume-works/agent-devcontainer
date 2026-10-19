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

# The server always requires a password. A Coder-provided one may face every
# interface; a generated one stays on localhost, read by the pane from its file
# so it never appears on a command line. DISPLAY is dropped so no browser opens.
serve="opencode serve --port 4096 --hostname"
password_note=""
if [[ -n "${OPENCODE_SERVER_PASSWORD:-}" ]]; then
  pane_command="exec env -u DISPLAY $serve 0.0.0.0"
else
  password_file="$HOME/.local/share/opencode/agentdev-server-password"
  if [[ ! -s "$password_file" ]]; then
    mkdir -p "${password_file%/*}"
    (umask 077 && head -c 32 /dev/urandom | base64 | tr -d '\n/+=' >"$password_file")
  fi
  pane_command="exec bash -c 'OPENCODE_SERVER_PASSWORD=\"\$(cat \"\$1\")\" exec env -u DISPLAY $serve 127.0.0.1' opencode-web $(printf '%q' "$password_file")"
  password_note=" (password in $password_file)"
fi

if tmux -L "$session" has-session -t "=$session" 2>/dev/null; then
  echo "OpenCode web tmux session '$session' is already running: $link$password_note"
  exit 0
fi

tmux_start=(tmux -L "$session" start-server \; new-session -d -s "$session" -c "$workspace" \
  "$pane_command")

if ! tmux_error="$("${tmux_start[@]}" 2>&1)"; then
  if tmux -L "$session" has-session -t "=$session" 2>/dev/null; then
    echo "OpenCode web tmux session '$session' is already running: $link$password_note"
    exit 0
  fi
  printf 'Failed to start OpenCode web: %s\n' "$tmux_error" >&2
  exit 1
fi

echo "Started OpenCode web in tmux session '$session' on port 4096: $link$password_note"
