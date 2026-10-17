#!/usr/bin/env bash
set -euo pipefail

# Readiness probes for the standalone runtime's services, and the aggregate
# readiness the image HEALTHCHECK reads. Exit 0 means ready.
# Usage: runtime-health.sh docker|dbus|keyring|cbm|xpra|opencode|ready

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
service="${1:-}"

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
  docker) timeout 10 docker info >/dev/null 2>&1 ;;
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
  ready) [[ -f ${AGENTDEV_RUN_DIR:-/run/agentdev}/ready ]] ;;
  *)
    echo "usage: $(basename "$0") docker|dbus|keyring|cbm|xpra|opencode|ready" >&2
    exit 2
    ;;
esac
