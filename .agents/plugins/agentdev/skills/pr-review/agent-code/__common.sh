#!/usr/bin/env bash

set -euo pipefail

skill_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

print_error() {
  printf 'ERROR: %s\n' "$*" >&2
}

# shellcheck source=/dev/null
source "${skill_script_dir}/../../../bin/result-codes.sh"

require_arg() {
  local name="$1" value="$2"
  if [[ -z "${value}" ]]; then
    print_error "Missing required argument: ${name}"
    quit_by_code 2
  fi
}

require_gh() {
  command -v gh >/dev/null 2>&1 || { print_error "gh CLI not found on PATH."; quit_by_code 2; }
  gh auth status >/dev/null 2>&1 || { print_error "gh is not authenticated."; quit_by_code 2; }
}

require_jq() {
  command -v jq >/dev/null 2>&1 || { print_error "jq not found on PATH."; quit_by_code 2; }
}

require_body_file() {
  local body_file="$1"
  if [[ ! -f "${body_file}" ]]; then
    print_error "Body file not found: ${body_file}. Write the text with the Write tool first, then pass its path."
    quit_by_code 2
  fi
}

# Prints "<owner>/<name>" for the current repo
resolve_repo() {
  gh repo view --json nameWithOwner -q .nameWithOwner
}
