#!/usr/bin/env bash
set -euo pipefail

# OpenCode server command and link construction shared by the Coder tmux launcher and
# the standalone supervisor. Spec: opencode-web, standalone-opencode-runtime.
# Usage: opencode-web-command.sh link|coder-hostname|coder-pane|serve|probe

port="${AGENTDEV_OPENCODE_PORT:-4096}"
workspace="${DEV_WORKSPACE_FOLDER:-$PWD}"

fail() {
  echo "opencode-web-command: $*" >&2
  exit 1
}

# The web UI opens a directory at /<base64url, unpadded>/session; Coder's agent
# sets VSCODE_PROXY_URI to its port-URL template.
link() {
  local local_url_template="http://127.0.0.1:{{port}}" base encoded
  base="${VSCODE_PROXY_URI:-$local_url_template}"
  base="${base//\{\{port\}\}/$port}"
  encoded="$(printf '%s' "$workspace" | base64 | tr -d '\n=' | tr '+/' '-_')"
  printf '%s\n' "${base%/}/$encoded/session"
}

# Listening beyond localhost requires the server password OpenCode enforces.
coder_hostname() {
  if [[ -n ${OPENCODE_SERVER_PASSWORD:-} ]]; then
    echo 0.0.0.0
  else
    echo 127.0.0.1
  fi
}

require_password() {
  [[ -n ${OPENCODE_SERVER_PASSWORD:-} ]] ||
    fail "OPENCODE_SERVER_PASSWORD must be set to a nonempty value; the server listens on the proxy network"
}

# Readiness is the authenticated health API, never an unauthenticated page.
probe() {
  local user="${OPENCODE_SERVER_USERNAME:-opencode}" secret="${OPENCODE_SERVER_PASSWORD:-}"
  secret="${secret//\\/\\\\}"
  secret="${secret//\"/\\\"}"
  printf 'user = "%s:%s"\n' "$user" "$secret" |
    curl -fsS --max-time 5 --config - "http://127.0.0.1:$port/global/health" |
    jq -e '.healthy == true' >/dev/null
}

case "${1:-}" in
  link) link ;;
  coder-hostname) coder_hostname ;;
  # Without DISPLAY, `opencode web` cannot open a browser on the Xpra desktop.
  coder-pane) echo "exec env -u DISPLAY opencode web --port $port --hostname $(coder_hostname)" ;;
  serve)
    require_password
    command -v opencode >/dev/null || fail "opencode is not installed"
    cd "$workspace"
    # `serve` opens no browser, so DISPLAY stays for graphical tools OpenCode runs.
    exec opencode serve --port "$port" --hostname 0.0.0.0
    ;;
  probe)
    require_password
    probe
    ;;
  *)
    echo "usage: $(basename "$0") link|coder-hostname|coder-pane|serve|probe" >&2
    exit 2
    ;;
esac
