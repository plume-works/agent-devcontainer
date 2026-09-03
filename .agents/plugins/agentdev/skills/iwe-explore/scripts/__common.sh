#!/usr/bin/env bash

set -euo pipefail

skill_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
skill_root_dir="$(cd -- "${skill_script_dir}/.." && pwd)"

print_error() {
  printf 'ERROR: %s\n' "$*" >&2
}

# shellcheck source=/dev/null
source "${skill_script_dir}/../../../bin/result-codes.sh"
# shellcheck source=/dev/null
source "${skill_script_dir}/../../../bin/github-issue.sh"

# shellcheck disable=SC2034  # repo_root is read by the sourcing script
require_git_repo() {
  if ! repo_root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
    print_error "This script must be run inside a Git repository."
    quit_by_code 2
  fi
}

show_help_header() {
  local description="$1"

  printf '%s\n\n' "${description}"
  printf 'Skill root: %s\n' "${skill_root_dir}"
}
