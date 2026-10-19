#!/usr/bin/env bash
set -euo pipefail

# Lifecycle adapter over codebase-memory-mcp's public `daemon start|status|stop`.
# A daemon generation is its PID plus kernel start time, so a reused PID is never
# mistaken for, or killed as, the daemon this adapter started or adopted.

usage() {
  echo "usage: $(basename "$0") install|start|check|index <repo-path>|run|stop" >&2
  exit 2
}

cbm_bin="${AGENTDEV_CBM_BIN:-$(command -v codebase-memory-mcp || true)}"
state_dir="${AGENTDEV_CBM_STATE_DIR:-${XDG_RUNTIME_DIR:-/tmp}/agentdev-cbm-$(id -u)}"
generation_file="$state_dir/generation"
start_timeout="${AGENTDEV_CBM_START_TIMEOUT:-60}"
stop_timeout="${AGENTDEV_CBM_STOP_TIMEOUT:-30}"
index_timeout="${AGENTDEV_CBM_INDEX_TIMEOUT:-1800}"
poll_interval="${AGENTDEV_CBM_POLL_INTERVAL:-2}"
unresponsive_limit="${AGENTDEV_CBM_UNRESPONSIVE_LIMIT:-3}"

log() { echo "runtime-cbm: $*" >&2; }

require_environment() {
  if [[ -z $cbm_bin || ! -x $cbm_bin ]]; then
    log "codebase-memory-mcp is not installed"
    exit 1
  fi
  if [[ -z ${CBM_CACHE_DIR:-} ]]; then
    log "CBM_CACHE_DIR is required"
    exit 1
  fi
  mkdir -p "$state_dir"
  chmod 700 "$state_dir"
}

process_start_time() {
  local stat
  stat="$(cat "/proc/$1/stat" 2>/dev/null)" || return 1
  # Field 22 counts from after the parenthesised command name, which may hold spaces.
  stat="${stat##*) }"
  read -r -a fields <<<"$stat"
  echo "${fields[19]}"
}

# Prints "<pid> <mode>" for the daemon `daemon status` reports healthy.
# Returns 3 when none is running and 4 when the endpoint holder does not answer.
daemon_status() {
  local output rc=0
  output="$("$cbm_bin" daemon status 2>&1)" || rc=$?
  if ((rc == 0)) && [[ $output =~ daemon:\ active\ \(([a-z-]+)\).*pid:\ ([0-9]+) ]]; then
    echo "${BASH_REMATCH[2]} ${BASH_REMATCH[1]}"
    return 0
  fi
  if [[ $output == *"not responding"* ]]; then
    [[ $output =~ held\ by\ pid\ ([0-9]+) ]] && echo "${BASH_REMATCH[1]} unresponsive"
    return 4
  fi
  return 3
}

record_generation() {
  local pid="$1" started
  started="$(process_start_time "$pid")" || return 1
  echo "$pid $started" >"$generation_file.new"
  mv "$generation_file.new" "$generation_file"
}

read_generation() {
  [[ -f $generation_file ]] || return 1
  read -r tracked_pid tracked_start <"$generation_file"
}

generation_alive() {
  local current
  current="$(process_start_time "$1")" || return 1
  [[ $current == "$2" ]]
}

# Kill only the process whose PID *and* start time match the recorded generation.
kill_generation() {
  local pid="$1" started="$2" deadline
  generation_alive "$pid" "$started" || return 0
  kill -TERM "$pid" 2>/dev/null || return 0
  deadline=$((SECONDS + 5))
  while generation_alive "$pid" "$started" && ((SECONDS < deadline)); do sleep 0.2; done
  if generation_alive "$pid" "$started"; then
    log "daemon pid $pid ignored SIGTERM; sending SIGKILL"
    kill -KILL "$pid" 2>/dev/null || true
  fi
}

cmd_install() {
  require_environment
  local install_dir="${CBM_INSTALL_DIR:-$HOME/.local/bin}"
  local staged="$install_dir/codebase-memory-mcp"
  # The native installer refuses to stage from a directory the caller does not own,
  # so publish an exact copy of the image's pinned binary into a user-owned one.
  if [[ $(realpath "$cbm_bin") != $(realpath -m "$staged") ]]; then
    (umask 077 && mkdir -p "$install_dir")
    chmod 700 "$install_dir"
    if ! cmp -s "$cbm_bin" "$staged"; then
      install -m 0755 "$cbm_bin" "$staged.new"
      mv -f "$staged.new" "$staged"
    fi
  fi
  PATH="$install_dir:$PATH" CBM_INSTALL_DIR="$install_dir" \
    "$(dirname "${BASH_SOURCE[0]}")/codebase-memory-mcp-install.sh"
  if ! cmp -s "$cbm_bin" "$staged"; then
    log "installed $staged differs from the image binary $cbm_bin"
    exit 1
  fi
}

cmd_start() {
  require_environment
  local output rc=0 status pid deadline
  output="$(timeout "$start_timeout" "$cbm_bin" daemon start 2>&1)" || rc=$?
  echo "$output" >&2
  if ((rc != 0)); then
    log "daemon start failed with exit code $rc"
    return 1
  fi
  deadline=$((SECONDS + start_timeout))
  until status="$(daemon_status)"; do
    if ((SECONDS >= deadline)); then
      log "daemon did not report active within ${start_timeout}s"
      return 1
    fi
    sleep 0.5
  done
  pid="${status%% *}"
  record_generation "$pid"
  log "ready: pid $pid (${status#* })"
}

# Exit 0: tracked generation healthy. 3: not running. 4: unresponsive.
# 5: a different generation (for example, one an MCP client auto-started) is active.
cmd_check() {
  require_environment
  local status rc=0
  status="$(daemon_status)" || rc=$?
  if ((rc != 0)); then
    return "$rc"
  fi
  if read_generation && [[ ${status%% *} == "$tracked_pid" ]] &&
    generation_alive "$tracked_pid" "$tracked_start"; then
    return 0
  fi
  log "daemon generation changed: now pid ${status%% *} (${status#* })"
  return 5
}

cmd_index() {
  require_environment
  [[ -n ${1:-} ]] || usage
  timeout "$index_timeout" "$cbm_bin" cli --quiet index_repository --repo-path "$1" >/dev/null
}

cmd_stop() {
  require_environment
  local rc=0 deadline
  read_generation || { tracked_pid="" && tracked_start=""; }
  timeout "$stop_timeout" "$cbm_bin" daemon stop >&2 || rc=$?
  ((rc == 0)) || log "daemon stop exited $rc; bounding cleanup of the tracked generation"
  if [[ -n $tracked_pid ]]; then
    deadline=$((SECONDS + stop_timeout))
    while generation_alive "$tracked_pid" "$tracked_start" && ((SECONDS < deadline)); do
      sleep 0.2
    done
    kill_generation "$tracked_pid" "$tracked_start"
  fi
  rm -f "$generation_file"
}

# Foreground mode for a supervisor: exits nonzero when the tracked daemon dies,
# is replaced, or stops answering; SIGTERM stops the daemon before exiting.
cmd_run() {
  local stopping=0 unresponsive=0 rc
  trap 'stopping=1' TERM INT
  cmd_start
  while ((stopping == 0)); do
    sleep "$poll_interval" &
    wait $! || true
    ((stopping == 0)) || break
    rc=0
    cmd_check || rc=$?
    case "$rc" in
      0) unresponsive=0 ;;
      4)
        unresponsive=$((unresponsive + 1))
        if ((unresponsive >= unresponsive_limit)); then
          log "daemon unresponsive for $unresponsive checks"
          read_generation || return 1
          kill_generation "$tracked_pid" "$tracked_start"
          return 1
        fi
        ;;
      *)
        log "tracked daemon generation lost (check exit $rc)"
        return 1
        ;;
    esac
  done
  cmd_stop
}

case "${1:-}" in
  install) cmd_install ;;
  start) cmd_start ;;
  check) cmd_check ;;
  index) cmd_index "${2:-}" ;;
  run) cmd_run ;;
  stop) cmd_stop ;;
  *) usage ;;
esac
