#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
merge_script="${script_dir}/../../git-merge-resolve/agent-code/git-merge-resolve.sh"
# shellcheck source=/dev/null
source "${script_dir}/__common.sh"

RESULT_CODES+=("3=ALREADY_UP_TO_DATE" "4=MERGE_CONFLICTS" "5=PROTECTED_BRANCH" "6=FETCH_FAILED")

remote_name="origin"
base_branch="main"

usage() {
  show_help_header "Merge origin/main into the current branch."
  cat <<'EOF'

Usage:
  update-branch.sh [--remote <name>] [--base <branch>]

Options:
  --remote <name>    Remote to fetch from. Default: origin
  --base <branch>    Base branch to merge. Default: main
  -h, --help         Show this help text.

Output (key=value lines):
  RESULT, BRANCH, REMOTE, BASE
  The delegated merge also prints DESTINATION and SOURCE.

Results (RESULT / exit code):
  SUCCESS            0  Merge succeeded
  ALREADY_UP_TO_DATE 3  Branch already contains the base ref
  MERGE_CONFLICTS    4  Conflicts detected — use the git-merge-resolve workflow
  PROTECTED_BRANCH   5  Current branch is the default branch
  FETCH_FAILED       6  The configured remote could not be fetched
  PREFLIGHT_ERROR    2  Usage or preflight error (not a repo, dirty tree)
  SCRIPT_FAILURE     1  Unhandled error

Examples:
  agent-code/update-branch.sh
  agent-code/update-branch.sh --remote upstream --base main
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote)
      [[ $# -ge 2 ]] || { print_error "Missing value for --remote"; quit_by_code 2; }
      remote_name="$2"
      shift 2
      ;;
    --base)
      [[ $# -ge 2 ]] || { print_error "Missing value for --base"; quit_by_code 2; }
      base_branch="$2"
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

branch_name="$(current_branch)"

if is_default_branch "${branch_name}"; then
  print_error "Current branch is '${branch_name}'. Refusing to merge '${base_branch}' into the default branch."
  quit_by_code 5
fi

# Preflight: clean working tree
if [[ -n "$(git status --porcelain)" ]]; then
  print_error "Working tree is dirty. Commit or stash changes before updating the branch."
  git status --short >&2
  quit_by_code 2
fi

printf 'BRANCH=%s\n' "${branch_name}"
printf 'REMOTE=%s\n' "${remote_name}"
printf 'BASE=%s/%s\n' "${remote_name}" "${base_branch}"

# Fetch
printf 'Fetching %s...\n' "${remote_name}" >&2
if ! git fetch "${remote_name}"; then
  print_error "Failed to fetch remote '${remote_name}'."
  quit_by_code 6
fi

base_ref="${remote_name}/${base_branch}"

if ! git rev-parse --verify --quiet "${base_ref}^{commit}" >/dev/null; then
  print_error "Base branch '${base_ref}' was not found after fetching '${remote_name}'."
  quit_by_code 2
fi

# Check if already up to date
merge_base="$(git merge-base HEAD "${base_ref}")"
base_sha="$(git rev-parse "${base_ref}")"

if [[ "${merge_base}" == "${base_sha}" ]]; then
  printf 'Already up to date with %s.\n' "${base_ref}" >&2
  quit_by_code 3
fi

# Delegate merge execution and any conflict handling to the generic skill. Its
# result table is aligned with this one (0/1/2 shared, 3=ALREADY_UP_TO_DATE,
# 4=MERGE_CONFLICTS), so exec hands it the process and its RESULT line becomes
# this run's one verdict — no translation layer, no filtered output. exec also
# discards this script's EXIT trap, so guard the one case that would have
# needed it.
if [[ ! -x "${merge_script}" ]]; then
  print_error "Merge helper is missing or not executable: ${merge_script}"
  quit_by_code 1
fi

exec "${merge_script}" \
  --message "Merge ${base_ref} into ${branch_name}" \
  "${base_ref}"
