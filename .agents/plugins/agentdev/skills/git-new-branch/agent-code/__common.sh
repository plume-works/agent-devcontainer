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
source "${skill_script_dir}/../../../bin/git-default-branch.sh"

require_git_repo() {
  if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
    print_error "This script must be run inside a Git repository."
    quit_by_code 2
  fi
}

# The main checkout owns the shared Git directory; linked worktrees point into it.
main_checkout_dir() {
  local common_dir
  common_dir="$(git rev-parse --path-format=absolute --git-common-dir)" || return 1
  dirname -- "${common_dir}"
}

show_help_header() {
  local description="$1"

  printf '%s\n\n' "${description}"
  printf 'Skill root: %s\n' "${skill_root_dir}"
}
