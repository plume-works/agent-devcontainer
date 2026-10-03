#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

source_ref=""
merge_message=""

print_error() {
  printf 'ERROR: %s\n' "$*" >&2
}

# shellcheck source=/dev/null
source "${script_dir}/../../../bin/result-codes.sh"

# These numbers and names are shared with update-branch.sh, which execs this
# script and passes its verdict straight through. Keep the two tables aligned.
RESULT_CODES+=("3=ALREADY_UP_TO_DATE" "4=MERGE_CONFLICTS")

usage() {
  cat <<'EOF'
Merge a local Git ref into the current branch with a non-fast-forward merge.

Usage:
  git-merge-resolve.sh [--message <text>] <source-ref>

Options:
  --message <text>  Merge commit message. Defaults to a generated message.
  -h, --help        Show this help text.

Output (key=value lines):
  RESULT
  Once preflight passes also: DESTINATION, SOURCE

Results (RESULT / exit code):
  SUCCESS            0  Merge succeeded
  ALREADY_UP_TO_DATE 3  Source ref is already merged into HEAD
  MERGE_CONFLICTS    4  Conflicts detected; resolve and commit them
  PREFLIGHT_ERROR    2  Usage, repository, ref, or working-tree preflight
                        failed, or the merge failed with no unresolved paths
  SCRIPT_FAILURE     1  Unhandled error

Examples:
  agent-code/git-merge-resolve.sh topic
  agent-code/git-merge-resolve.sh \
    --message "Merge origin/main into feature" origin/main
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --message)
      [[ $# -ge 2 ]] || { print_error "Missing value for --message"; quit_by_code 2; }
      merge_message="$2"
      shift 2
      ;;
    -h|--help)
      usage
      quit_by_code 0
      ;;
    --*)
      print_error "Unknown option: $1"
      usage >&2
      quit_by_code 2
      ;;
    *)
      if [[ -n "${source_ref}" ]]; then
        print_error "Only one source ref may be supplied."
        usage >&2
        quit_by_code 2
      fi
      source_ref="$1"
      shift
      ;;
  esac
done

if [[ -z "${source_ref}" ]]; then
  print_error "A source ref is required."
  usage >&2
  quit_by_code 2
fi

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  print_error "This script must be run inside a Git repository."
  quit_by_code 2
fi

if [[ "$(git rev-parse --abbrev-ref HEAD)" == "HEAD" ]]; then
  print_error "Detached HEAD cannot receive this merge. Check out a branch first."
  quit_by_code 2
fi

if [[ -f "$(git rev-parse --git-path MERGE_HEAD)" ]]; then
  print_error "A merge is already in progress. Resolve or complete it first."
  git status --short >&2
  quit_by_code 2
fi

if [[ -n "$(git status --porcelain)" ]]; then
  print_error "Working tree is dirty. Commit or stash changes before merging."
  git status --short >&2
  quit_by_code 2
fi

if ! git rev-parse --verify --quiet "${source_ref}^{commit}" >/dev/null; then
  print_error "Source ref does not resolve to a commit: ${source_ref}"
  quit_by_code 2
fi

destination_branch="$(git rev-parse --abbrev-ref HEAD)"
source_sha="$(git rev-parse "${source_ref}^{commit}")"

printf 'DESTINATION=%s\n' "${destination_branch}"
printf 'SOURCE=%s\n' "${source_ref}"

if git merge-base --is-ancestor "${source_sha}" HEAD; then
  printf '%s is already merged into %s.\n' \
    "${source_ref}" "${destination_branch}" >&2
  quit_by_code 3
fi

if [[ -z "${merge_message}" ]]; then
  merge_message="Merge ${source_ref} into ${destination_branch}"
fi

printf 'Merging %s into %s...\n' "${source_ref}" "${destination_branch}" >&2
if git merge --no-ff "${source_ref}" --message "${merge_message}"; then
  git log --oneline --decorate -n 5
  quit_by_code 0
fi

conflicted_files="$(git diff --name-only --diff-filter=U)"
if [[ -z "${conflicted_files}" ]]; then
  print_error "Merge failed without unresolved paths. Inspect Git output and status."
  git status --short >&2
  quit_by_code 2
fi

print_error "Merge conflicts detected. Resolve the conflicts listed below."
printf '\nConflicted files:\n' >&2
printf '%s\n' "${conflicted_files}" >&2
quit_by_code 4
