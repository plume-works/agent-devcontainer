#!/usr/bin/env bash
set -euo pipefail

# Start phase (postStartCommand, the waitFor target): wait for the runtime's required
# services, repair per-start state, run the started hooks. --no-wait: no supervisor runs.
# Spec: agentdev-runtime-images. Usage: devcontainer-ready.sh [--no-wait]

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace="${DEV_WORKSPACE_FOLDER:-$PWD}"
export DEV_WORKSPACE_FOLDER="$workspace"
health="${AGENTDEV_HEALTH_COMMAND:-$script_dir/runtime-health.sh}"
timeout_s="${AGENTDEV_READY_TIMEOUT:-900}"

fail() {
  echo "devcontainer-ready: $*" >&2
  "$health" status >&2 || true
  exit 1
}

wait_ready() {
  local deadline=$((SECONDS + timeout_s)) state
  until "$health" ready >/dev/null 2>&1; do
    state="$("$health" status 2>/dev/null | head -n 1 || true)"
    [[ $state != "runtime state: failed" ]] || fail "the runtime failed; the editor cannot attach"
    ((SECONDS < deadline)) || fail "the runtime was not ready within ${timeout_s}s"
    sleep 1
  done
  echo "devcontainer-ready: the runtime's required services are ready"
}

case "${1:-}" in
  '') wait_ready ;;
  --no-wait) ;;
  *)
    echo "usage: $(basename "$0") [--no-wait]" >&2
    exit 2
    ;;
esac

"$script_dir/setup-git-safe-directory.sh"
# After the keyring: gh may keep its login there.
"$script_dir/setup-gh-credential-helper.sh"
# Repairs the shared auth.json symlink a `codex logout` can destroy; see link-codex-auth.sh.
"$script_dir/setup-agent-state.sh" links
"$script_dir/setup-agent-state.sh" agent-policy
"$script_dir/run-agentdev-hooks.sh" started
