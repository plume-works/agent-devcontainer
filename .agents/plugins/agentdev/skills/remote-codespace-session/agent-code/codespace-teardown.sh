#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${script_dir}/__common.sh"

RESULT_CODES+=("4=TEARDOWN_FAILED" "5=STATE_WAIT_TIMEOUT" "6=GH_CALL_FAILED")

delete=0
poll_interval=10
poll_timeout=300

usage() {
  show_help_header "Stop (default) or delete the codespace recorded by codespace-ensure.sh."
  cat <<'EOF'

Usage:
  codespace-teardown.sh [--delete] [--poll-interval <seconds>] [--poll-timeout <seconds>]

Options:
  --delete                    Fully delete the codespace instead of stopping it.
                               Skips gh's own interactive confirmation via --force.
  --poll-interval <seconds>   Seconds between state polls while waiting for the
                               terminal state. Integer >= 1. Default: 10
  --poll-timeout <seconds>    Total seconds to wait for the terminal state before
                               giving up. Integer >= 0. Default: 300
  -h, --help                  Show this help text.

Behavior:
  Default: 'gh codespace stop' -- stops compute billing, keeps storage so a
  later codespace-ensure.sh can reuse it. Does not touch ./.tmp/codespace-name
  or ./.tmp/codespace-ssh-config. Waits (polling like codespace-ensure.sh) until
  the codespace reports 'Shutdown', since 'gh codespace stop' returns while the
  codespace is still 'ShuttingDown'.
  --delete: 'gh codespace delete --force' -- fully deletes the codespace, waits
  until it disappears from 'gh codespace list', then removes
  ./.tmp/codespace-name and ./.tmp/codespace-ssh-config since they now refer to
  a codespace that no longer exists.

Output (key=value lines):
  RESULT, ACTION, CODESPACE
  ACTION=stop also prints: STATE

Results (RESULT / exit code):
  SUCCESS                  0  Stopped (reached Shutdown) or deleted (gone from the list)
  TEARDOWN_FAILED          4  The 'gh codespace stop' or 'gh codespace delete' call failed
  STATE_WAIT_TIMEOUT       5  Timed out waiting for the terminal state (Shutdown for stop,
                              gone for delete). The stop/delete itself was accepted; only
                              the wait timed out. Re-check with 'gh codespace list'
  GH_CALL_FAILED           6  A 'gh codespace list' lookup failed
  CODESPACE_SCOPE_MISSING  3  gh token is missing the 'codespace' OAuth scope
  PREFLIGHT_ERROR          2  Usage error, not a repo, gh missing or unauthenticated,
                              or no codespace name recorded
  SCRIPT_FAILURE           1  Unhandled error

Examples:
  agent-code/codespace-teardown.sh
  agent-code/codespace-teardown.sh --delete
  agent-code/codespace-teardown.sh --poll-timeout 600
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --delete)
      delete=1
      shift
      ;;
    --poll-interval)
      [[ $# -ge 2 ]] || { print_error "Missing value for --poll-interval"; quit_by_code 2; }
      require_int_min "--poll-interval" "$2" 1
      poll_interval="$2"
      shift 2
      ;;
    --poll-timeout)
      [[ $# -ge 2 ]] || { print_error "Missing value for --poll-timeout"; quit_by_code 2; }
      require_int_min "--poll-timeout" "$2" 0
      poll_timeout="$2"
      shift 2
      ;;
    -h|--help)
      usage
      quit_by_code 0
      ;;
    *)
      print_error "Unknown argument: $1"
      usage >&2
      quit_by_code 2
      ;;
  esac
done

require_git_repo
require_gh
require_codespace_auth

owner_repo="$(resolve_owner_repo)" || quit_by_code 2
name="$(read_codespace_name)" || quit_by_code 2

if [[ "${delete}" -eq 1 ]]; then
  status=0
  delete_output="$(gh codespace delete -c "${name}" --force 2>&1)" || status=$?
  if [[ "${status}" -ne 0 ]]; then
    print_error "gh codespace delete failed: ${delete_output}"
    quit_by_code 4
  fi

  # Wait until the codespace no longer appears in the list. quit_by_code must
  # run in this shell, not in the command substitution, so its RESULT line
  # reaches stdout instead of being captured into `state`.
  elapsed=0
  while :; do
    if ! state="$(codespace_state_by_name "${owner_repo}" "${name}")"; then
      print_error "Could not read the state of codespace ${name}. The delete was accepted; check 'gh codespace list'."
      quit_by_code 6
    fi
    [[ -n "${state}" ]] || break
    if [[ "${elapsed}" -ge "${poll_timeout}" ]]; then
      print_error "Timed out after ${poll_timeout}s waiting for codespace ${name} to be deleted (last state: ${state}). The delete was accepted; check 'gh codespace list'."
      quit_by_code 5
    fi
    sleep "${poll_interval}"
    elapsed=$((elapsed + poll_interval))
  done

  rm -f "$(codespace_name_file)" "$(ssh_config_file)"

  printf 'ACTION=delete\n'
  printf 'CODESPACE=%s\n' "${name}"
  quit_by_code 0
fi

status=0
stop_output="$(gh codespace stop -c "${name}" 2>&1)" || status=$?
if [[ "${status}" -ne 0 ]]; then
  print_error "gh codespace stop failed: ${stop_output}"
  quit_by_code 4
fi

# 'gh codespace stop' returns while the codespace is still 'ShuttingDown';
# wait until it settles at 'Shutdown' so callers don't reinvent this loop.
elapsed=0
while :; do
  if ! state="$(codespace_state_by_name "${owner_repo}" "${name}")"; then
    print_error "Could not read the state of codespace ${name}. The stop was accepted; check 'gh codespace list'."
    quit_by_code 6
  fi
  [[ "${state}" != "Shutdown" ]] || break
  if [[ "${elapsed}" -ge "${poll_timeout}" ]]; then
    print_error "Timed out after ${poll_timeout}s waiting for codespace ${name} to reach Shutdown (last state: ${state}). The stop was accepted; check 'gh codespace list'."
    quit_by_code 5
  fi
  sleep "${poll_interval}"
  elapsed=$((elapsed + poll_interval))
done

printf 'ACTION=stop\n'
printf 'CODESPACE=%s\n' "${name}"
printf 'STATE=Shutdown\n'
quit_by_code 0
