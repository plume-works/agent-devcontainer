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
  show_help_header "Bring in the branch's upstream, then merge origin/main into the current branch."
  cat <<'EOF'

Usage:
  update-branch.sh [--remote <name>] [--base <branch>]

Options:
  --remote <name>    Remote to fetch from. Default: origin
  --base <branch>    Base branch to merge. Default: main
  -h, --help         Show this help text.

Output (key=value lines):
  RESULT, BRANCH, REMOTE, BASE, UPSTREAM, UPSTREAM_ACTION
  Each delegated merge also prints DESTINATION and SOURCE.

UPSTREAM_ACTION says how the branch's upstream was brought in before the base:
'none', 'fast-forward', 'merge', 'untracked' (no upstream), 'base' (the
upstream is the base ref), or 'gone' (deleted on its remote; a warning).

A run stops at the first conflicted merge, and SOURCE names it. Rerun after
the resolution is committed; the rerun continues with the next merge.

Results (RESULT / exit code):
  SUCCESS            0  A merge commit was created
  ALREADY_UP_TO_DATE 3  Branch already contains the base ref; no merge commit
  MERGE_CONFLICTS    4  Conflicts detected — use the git-merge-resolve workflow
  PROTECTED_BRANCH   5  Current branch is the default branch
  FETCH_FAILED       6  The configured or upstream remote could not be fetched
  PREFLIGHT_ERROR    2  Usage or preflight error (not a repo, dirty tree)
  SCRIPT_FAILURE     1  Unhandled error

Examples:
  agent-code/update-branch.sh
  agent-code/update-branch.sh --remote upstream --base main
EOF
}

# Merge `source` through git-merge-resolve.sh, forwarding all of its stdout but
# its RESULT line; stops the run unless the merge succeeded.
merge_ref() {
  local source="$1"
  local helper_status=0
  local helper_output

  helper_output="$("${merge_script}" --message "Merge ${source} into ${branch_name}" "${source}")" ||
    helper_status=$?
  printf '%s\n' "${helper_output}" | grep -v '^RESULT=' || true

  case "${helper_status}" in
    0) merged=1 ;;
    4) quit_by_code 4 ;;
    2) quit_by_code 2 ;;
    *) quit_by_code 1 ;;
  esac
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

if [[ ! -x "${merge_script}" ]]; then
  print_error "Merge helper is missing or not executable: ${merge_script}"
  quit_by_code 1
fi

upstream_ref="$(git for-each-ref --format='%(upstream:short)' "refs/heads/${branch_name}")"
upstream_remote="$(git config --get "branch.${branch_name}.remote" || true)"
upstream_merge="$(git config --get "branch.${branch_name}.merge" || true)"

# Print how the upstream relates to HEAD; fetches a second upstream remote and
# stops the run when that remote cannot be reached.
classify_upstream() {
  local ls_remote_status=0

  if [[ -z "${upstream_ref}" ]]; then
    echo "untracked"
    return
  fi
  if [[ "${upstream_ref}" == "${base_ref}" ]]; then
    echo "base"
    return
  fi
  if [[ "${upstream_remote}" != "." ]]; then
    if [[ "${upstream_remote}" != "${remote_name}" ]]; then
      printf 'Fetching %s...\n' "${upstream_remote}" >&2
      if ! git fetch "${upstream_remote}" >&2; then
        print_error "Failed to fetch upstream remote '${upstream_remote}'."
        return 6
      fi
    fi
    git ls-remote --exit-code --heads "${upstream_remote}" "${upstream_merge#refs/heads/}" \
      >/dev/null || ls_remote_status=$?
    if [[ "${ls_remote_status}" -eq 2 ]]; then
      echo "gone"
      return
    elif [[ "${ls_remote_status}" -ne 0 ]]; then
      print_error "Failed to query upstream remote '${upstream_remote}'."
      return 6
    fi
  fi
  if git merge-base --is-ancestor "${upstream_ref}" HEAD; then
    echo "none"
  elif git merge-base --is-ancestor HEAD "${upstream_ref}"; then
    echo "fast-forward"
  else
    echo "merge"
  fi
}

upstream_action="$(classify_upstream)" || quit_by_code "$?"
printf 'UPSTREAM=%s\n' "${upstream_ref}"
printf 'UPSTREAM_ACTION=%s\n' "${upstream_action}"

merged=0
case "${upstream_action}" in
  gone)
    printf "WARNING: Upstream '%s' no longer exists on '%s'; continuing without it.\n" \
      "${upstream_ref}" "${upstream_remote}" >&2
    ;;
  fast-forward)
    git merge --ff-only --quiet "${upstream_ref}" >&2
    ;;
  merge)
    merge_ref "${upstream_ref}"
    ;;
esac

if git merge-base --is-ancestor "${base_ref}" HEAD; then
  printf 'Already contains %s.\n' "${base_ref}" >&2
  if [[ "${merged}" -eq 1 ]]; then
    quit_by_code 0
  fi
  quit_by_code 3
fi

merge_ref "${base_ref}"
quit_by_code 0
