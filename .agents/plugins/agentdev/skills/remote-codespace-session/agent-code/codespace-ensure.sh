#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${script_dir}/__common.sh"

RESULT_CODES+=("4=CREATE_FAILED" "5=STATE_WAIT_TIMEOUT" "6=GH_CALL_FAILED")

branch=""
machine="standardLinux32gb"
idle_timeout="30m"
retention_period="24h"
poll_interval=10
poll_timeout=300
dry_run=0

usage() {
  show_help_header "Find-or-create the Codespace used as this session's remote build/test machine."
  cat <<'EOF'

Usage:
  codespace-ensure.sh [--branch <name>] [--machine <name>] [--idle-timeout <dur>]
                       [--retention-period <dur>] [--poll-interval <seconds>]
                       [--poll-timeout <seconds>] [--dry-run]

Options:
  --branch <name>             Branch to create/find the codespace for. Default: current branch
  --machine <name>            gh codespace create -m value. Default: standardLinux32gb
  --idle-timeout <dur>        gh codespace create --idle-timeout value. Default: 30m
  --retention-period <dur>    gh codespace create --retention-period value. Go-style
                               duration (h/m/s only, no 'd'; max 720h). Default: 24h
  --poll-interval <seconds>   Seconds between state polls while waiting for a new codespace.
                               Integer >= 1. Default: 10
  --poll-timeout <seconds>    Total seconds to wait before giving up. Integer >= 0. Default: 300
  --dry-run                   Print what would happen without creating anything or writing
                               ./.tmp/codespace-name
  -h, --help                  Show this help text.

Output (key=value lines):
  RESULT, ACTION
  ACTION=reuse, and ACTION=create outside --dry-run, also print: CODESPACE, STATE
  ACTION=create under --dry-run instead prints: DISPLAY_NAME, MACHINE,
  IDLE_TIMEOUT, RETENTION_PERIOD, BRANCH

Results (RESULT / exit code):
  SUCCESS                  0  Resolved (reused or created), or dry-run report printed
  CREATE_FAILED            4  'gh codespace create' failed
  STATE_WAIT_TIMEOUT       5  Timed out waiting for the new codespace to reach Available.
                              Its name was still recorded; check 'gh codespace list'
  GH_CALL_FAILED           6  A 'gh codespace list' lookup failed
  CODESPACE_SCOPE_MISSING  3  gh token is missing the 'codespace' OAuth scope
  PREFLIGHT_ERROR          2  Usage error, not a repo, detached HEAD, or gh missing
                              or unauthenticated
  SCRIPT_FAILURE           1  Unhandled error

Examples:
  agent-code/codespace-ensure.sh
  agent-code/codespace-ensure.sh --dry-run
  agent-code/codespace-ensure.sh --branch feature/my-change --machine premiumLinux
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch)
      [[ $# -ge 2 ]] || { print_error "Missing value for --branch"; quit_by_code 2; }
      branch="$2"
      shift 2
      ;;
    --machine)
      [[ $# -ge 2 ]] || { print_error "Missing value for --machine"; quit_by_code 2; }
      machine="$2"
      shift 2
      ;;
    --idle-timeout)
      [[ $# -ge 2 ]] || { print_error "Missing value for --idle-timeout"; quit_by_code 2; }
      idle_timeout="$2"
      shift 2
      ;;
    --retention-period)
      [[ $# -ge 2 ]] || { print_error "Missing value for --retention-period"; quit_by_code 2; }
      retention_period="$2"
      shift 2
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
    --dry-run)
      dry_run=1
      shift
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

if [[ -z "${branch}" ]]; then
  branch="$(current_branch)" || {
    print_error "Could not determine the current branch. Pass --branch <name>."
    quit_by_code 2
  }
  if [[ "${branch}" == "HEAD" ]]; then
    print_error "Detached HEAD: check out a branch, or pass --branch <name>."
    quit_by_code 2
  fi
fi

display_name="$(codespace_display_name "${branch}")"

existing_name="$(codespace_lookup_by_display_name "${owner_repo}" "${display_name}")" || {
  print_error "Could not list codespaces for ${owner_repo}. Check 'gh codespace list'."
  quit_by_code 6
}

if [[ -n "${existing_name}" ]]; then
  state="$(codespace_state_by_name "${owner_repo}" "${existing_name}")" || {
    print_error "Could not read the state of codespace ${existing_name}. Check 'gh codespace list'."
    quit_by_code 6
  }

  if [[ "${state}" != "Available" && "${state}" != "Shutdown" ]]; then
    printf 'NOTE: Codespace %s has unexpected state %s; reusing it anyway. A later ssh call is the real usability gate.\n' "${existing_name}" "${state}" >&2
  fi

  if [[ "${dry_run}" -eq 1 ]]; then
    printf 'ACTION=reuse\n'
    printf 'CODESPACE=%s\n' "${existing_name}"
    printf 'STATE=%s\n' "${state}"
    quit_by_code 0
  fi

  write_codespace_name "${existing_name}"
  printf 'ACTION=reuse\n'
  printf 'CODESPACE=%s\n' "${existing_name}"
  printf 'STATE=%s\n' "${state}"
  quit_by_code 0
fi

if [[ "${dry_run}" -eq 1 ]]; then
  printf 'ACTION=create\n'
  printf 'DISPLAY_NAME=%s\n' "${display_name}"
  printf 'MACHINE=%s\n' "${machine}"
  printf 'IDLE_TIMEOUT=%s\n' "${idle_timeout}"
  printf 'RETENTION_PERIOD=%s\n' "${retention_period}"
  printf 'BRANCH=%s\n' "${branch}"
  quit_by_code 0
fi

create_status=0
create_stderr_file="$(repo_root_tmp_dir)/codespace-ensure-create-stderr.$$"
create_stdout="$(gh codespace create -R "${owner_repo}" -b "${branch}" \
  --devcontainer-path .devcontainer/devcontainer.json \
  -m "${machine}" --idle-timeout "${idle_timeout}" \
  --retention-period "${retention_period}" --default-permissions \
  --display-name "${display_name}" 2>"${create_stderr_file}")" || create_status=$?
create_stderr="$(cat "${create_stderr_file}" 2>/dev/null || true)"
rm -f "${create_stderr_file}"

new_name="$(printf '%s' "${create_stdout}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

if [[ "${create_status}" -ne 0 || -z "${new_name}" ]]; then
  print_error "gh codespace create failed: ${create_stderr}"
  quit_by_code 4
fi

elapsed=0
state=""
while :; do
  # quit_by_code must run in this shell, not in the command substitution, so
  # its RESULT line reaches stdout instead of being captured into `state`.
  if ! state="$(codespace_state_by_name "${owner_repo}" "${new_name}")"; then
    print_error "Could not read the state of codespace ${new_name}. Check 'gh codespace list'."
    quit_by_code 6
  fi
  [[ "${state}" != "Available" ]] || break
  if [[ "${elapsed}" -ge "${poll_timeout}" ]]; then
    write_codespace_name "${new_name}"
    print_error "Timed out after ${poll_timeout}s waiting for codespace ${new_name} to become Available (last state: ${state}). Check 'gh codespace list' manually."
    quit_by_code 5
  fi
  sleep "${poll_interval}"
  elapsed=$((elapsed + poll_interval))
done

write_codespace_name "${new_name}"
printf 'ACTION=create\n'
printf 'CODESPACE=%s\n' "${new_name}"
printf 'STATE=Available\n'
quit_by_code 0
