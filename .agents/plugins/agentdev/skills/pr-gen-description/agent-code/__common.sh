#!/usr/bin/env bash

set -euo pipefail

skill_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
skill_root_dir="$(cd -- "${skill_script_dir}/.." && pwd)"

print_error() {
  printf 'ERROR: %s\n' "$*" >&2
}

# shellcheck source=/dev/null
source "${skill_script_dir}/../../../bin/result-codes.sh"

require_git_repo() {
  if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
    print_error "This script must be run inside a Git repository."
    quit_by_code 2
  fi
}

current_branch() {
  git rev-parse --abbrev-ref HEAD
}

is_default_branch() {
  local branch_name="$1"
  [[ "${branch_name}" == "main" || "${branch_name}" == "master" ]]
}

show_help_header() {
  local description="$1"

  printf '%s\n\n' "${description}"
  printf 'Skill root: %s\n' "${skill_root_dir}"
}
