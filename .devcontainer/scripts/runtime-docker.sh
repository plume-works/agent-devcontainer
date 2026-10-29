#!/usr/bin/env bash
set -euo pipefail

# The runtime's own nested Docker engine: exactly one root dockerd on a
# private Unix socket over per-instance storage, with no TCP listener and no host socket.
# Spec: standalone-opencode-runtime, devcontainer-docker-storage. Usage: runtime-docker.sh run

data_dir="${AGENTDEV_DOCKER_DATA_DIR:-/var/lib/docker}"
socket="${AGENTDEV_DOCKER_SOCKET:-/var/run/docker.sock}"
config="${AGENTDEV_DOCKER_CONFIG:-/etc/docker/daemon.json}"
exec_root="${AGENTDEV_DOCKER_EXEC_ROOT:-/var/run/docker}"
pidfile="${AGENTDEV_DOCKER_PIDFILE:-/var/run/docker.pid}"
proc_status="${AGENTDEV_PROC_STATUS:-/proc/self/status}"

fail() {
  echo "runtime-docker: $*" >&2
  exit 1
}

require_privileges() {
  local cap_eff
  [[ $(id -u) == 0 ]] || fail "dockerd must run as root"
  cap_eff="$(awk '/^CapEff:/ {print $2}' "$proc_status")"
  # CAP_SYS_ADMIN is bit 21; without it dockerd cannot mount its storage.
  (((16#$cap_eff >> 21) & 1)) ||
    fail "nested Docker needs a privileged container (compose: privileged: true)"
}

require_storage() {
  local fs_type
  mkdir -p "$data_dir"
  fs_type="$(stat -f -c %T "$data_dir")"
  [[ $fs_type != overlayfs ]] ||
    fail "$data_dir is on the container's overlay filesystem; mount a volume there"
}

require_private_endpoint() {
  [[ -f $config ]] || fail "$config is missing"
  # dockerd also refuses a hosts key alongside --host, so any listener here is an error.
  jq -e '(.hosts // []) | length == 0' "$config" >/dev/null ||
    fail "$config declares listeners (hosts); the engine listens only on $socket"
}

# Exactly one engine: a live dockerd behind the pid file means another start won.
require_single_engine() {
  local pid
  [[ -f $pidfile ]] || return 0
  pid="$(<"$pidfile")"
  if [[ -n $pid && -d /proc/$pid && $(cat "/proc/$pid/comm" 2>/dev/null) == dockerd ]]; then
    fail "dockerd is already running as pid $pid"
  fi
  rm -f "$pidfile" "$socket"
}

case "${1:-}" in
  run)
    require_privileges
    require_storage
    require_private_endpoint
    require_single_engine
    exec dockerd --config-file "$config" --data-root "$data_dir" --exec-root "$exec_root" \
      --pidfile "$pidfile" --host "unix://$socket" --group docker
    ;;
  *)
    echo "usage: $(basename "$0") run" >&2
    exit 2
    ;;
esac
