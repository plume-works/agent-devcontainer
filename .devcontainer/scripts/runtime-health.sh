#!/usr/bin/env bash
set -euo pipefail

# Readiness probes for the standalone runtime's services, the aggregate readiness the
# image HEALTHCHECK reads, and an operator status report. Exit 0 means ready.
# Usage: runtime-health.sh dockerd|dbus|keyring|cbm|xpra|opencode|ready|status

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
service="${1:-}"
run_dir="${AGENTDEV_RUN_DIR:-/run/agentdev}"
state_file="$run_dir/state.json"
record="${AGENTDEV_HOME:-$HOME}/.local/state/agentdev/last-failure.json"
retry="docker exec <container> $script_dir/runtime-supervisor.py retry"
# The controller's probe command, so tests can stand in for the real services.
probe="${AGENTDEV_HEALTH_COMMAND:-$0}"

# Prints the state file's state, or "stale" when its heartbeat is three intervals old.
current_state() {
  [[ -f $state_file ]] || { echo missing && return; }
  jq -r --argjson now "$(date +%s.%N)" '
      if ($now - (.heartbeat // 0)) < 3 * (.interval // 2) then .state else "stale" end
    ' "$state_file" 2>/dev/null || echo unreadable
}

# User services are probed as the runtime user: the session bus and the CBM
# rendezvous both admit only the account that owns them.
case "$service" in
  dbus | keyring | cbm | opencode | xpra)
    if [[ $(id -u) == 0 && -n ${AGENTDEV_USER:-} ]]; then
      exec setpriv --reuid="$AGENTDEV_USER" --regid="$(id -g "$AGENTDEV_USER")" --init-groups \
        env HOME="${AGENTDEV_HOME:-/home/$AGENTDEV_USER}" USER="$AGENTDEV_USER" "$0" "$service"
    fi
    ;;
esac

case "$service" in
  dockerd) timeout 10 docker info >/dev/null 2>&1 ;;
  dbus)
    timeout 5 gdbus call --session --dest org.freedesktop.DBus \
      --object-path /org/freedesktop/DBus --method org.freedesktop.DBus.GetId >/dev/null 2>&1
    ;;
  keyring) timeout 5 "$script_dir/runtime-keyring.sh" check ;;
  cbm) timeout 10 "$script_dir/runtime-cbm.sh" check 2>/dev/null ;;
  xpra)
    curl -fsS -o /dev/null --max-time 5 "http://127.0.0.1:${AGENTDEV_XPRA_PORT:-14500}/"
    ;;
  opencode) "$script_dir/opencode-web-command.sh" probe ;;
  ready)
    state="$(current_state)"
    if [[ $state != ready ]]; then
      echo "runtime state: $state"
      exit 1
    fi
    for core in dbus keyring opencode; do
      "$probe" "$core" >/dev/null 2>&1 || { echo "core probe failed: $core" && exit 1; }
    done
    ;;
  status)
    echo "runtime state: $(current_state)"
    [[ -f $state_file ]] || exit 1
    jq -r --arg retry "$retry" '
        .components | to_entries[]
        | select(.value.status == "failed" or .value.status == "blocked")
        | "  \(.key): \(.value.status)\(if .value.reason then " (\(.value.reason))" else "" end)"
          + (if .value.status == "failed" then "\n    retry: \($retry) \(.key)" else "" end)
      ' "$state_file"
    if [[ -f $record ]]; then
      jq -r '"last failure: \(.component), exit status \(.exit_status // "none"), at \(.time)"' \
        "$record"
      echo "  record: $record"
    fi
    [[ $(current_state) == ready ]]
    ;;
  *)
    echo "usage: $(basename "$0") dockerd|dbus|keyring|cbm|xpra|opencode|ready|status" >&2
    exit 2
    ;;
esac
