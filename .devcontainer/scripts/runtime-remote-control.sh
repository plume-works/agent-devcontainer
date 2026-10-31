#!/usr/bin/env bash
set -euo pipefail

# Waits for a claude.ai login, starts claude-remote, and exits once a session it saw is
# gone, so the controller's recovery budget restarts it. Spec: claude-remote-control.
# Usage: runtime-remote-control.sh run|check

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
session="claude-remote"
credentials="${CLAUDE_SECURESTORAGE_CONFIG_DIR:-${AGENTDEV_CLAUDE_DIR:-$HOME/.claude}}/.credentials.json"
status_file="${XDG_RUNTIME_DIR:?XDG_RUNTIME_DIR is required}/remote-control.status"
interval="${AGENTDEV_HEALTH_INTERVAL:-2}"

log() { echo "runtime-remote-control: $*" >&2; }

report() {
  printf '%s\n' "$1" >"$status_file.tmp"
  mv -f "$status_file.tmp" "$status_file"
}

# A login, a refresh, and an expiry all rewrite the credential file.
signature() { stat -L -c '%i %Y %s' "$credentials" 2>/dev/null || echo none; }

logged_in() {
  env -u CLAUDE_CODE_OAUTH_TOKEN claude auth status --json 2>/dev/null |
    jq -e '.loggedIn == true and .authMethod == "claude.ai"' >/dev/null 2>&1
}

live() { tmux -L "$session" has-session -t "=$session" 2>/dev/null; }

cmd_run() {
  local command checked="" current login=0 seen=""
  for command in claude tmux jq; do
    if ! command -v "$command" >/dev/null 2>&1; then
      log "$command is not installed"
      exit 1
    fi
  done
  # The start script rejects a set-but-empty spawn mode, which Compose passes through.
  [[ -n ${AGENTDEV_CLAUDE_RC_SPAWN:-} ]] || unset AGENTDEV_CLAUDE_RC_SPAWN
  while true; do
    current="$(signature)"
    if [[ $current != "$checked" ]]; then
      checked="$current"
      if logged_in; then login=1; else login=0; fi
    fi
    if ((login == 0)); then
      seen=""
      report "waiting for a claude.ai login"
    elif live; then
      seen=1
      report "running in tmux session $session"
    elif [[ -n $seen ]]; then
      log "tmux session $session is gone"
      exit 1
    else
      "$script_dir/claude-remote-control-start.sh"
      # A start that leaves no session counts as the session exiting, so the
      # controller's recovery budget bounds the retries.
      if ! live; then
        log "tmux session $session did not come up"
        exit 1
      fi
      seen=1
      report "running in tmux session $session"
    fi
    sleep "$interval"
  done
}

case "${1:-}" in
  run) cmd_run ;;
  check) [[ -s $status_file ]] ;;
  *)
    echo "usage: $(basename "$0") run|check" >&2
    exit 2
    ;;
esac
