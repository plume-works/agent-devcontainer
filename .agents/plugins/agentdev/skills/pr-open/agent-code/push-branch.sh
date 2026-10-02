#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${script_dir}/__common.sh"

RESULT_CODES+=("3=NOT_FAST_FORWARD" "4=PUSH_REJECTED" "5=PROTECTED_BRANCH")

remote_name="origin"
branch_name=""
remote_was_explicit=0

usage() {
  show_help_header "Push a branch to its pull request head ref without rewriting history."
  cat <<'EOF'

Usage:
  push-branch.sh [--remote <name>] [--branch <name>]

Options:
  --remote <name>    Remote to push to when no upstream is configured. Default: origin
  --branch <name>    Branch to push. Default: current branch
  -h, --help         Show this help text.

Output (key=value lines):
  RESULT, BRANCH, UPSTREAM, ACTION
  When the branch has an upstream also: AHEAD, BEHIND

ACTION says what was done: 'none' when the upstream already matched, 'push'
when an existing upstream was updated, and 'push-with-upstream' when the remote
branch was created and tracking configured.

Results (RESULT / exit code):
  SUCCESS           0  Pushed, or already up to date
  NOT_FAST_FORWARD  3  Branch is behind or diverged from its upstream
  PUSH_REJECTED     4  Push failed
  PROTECTED_BRANCH  5  Branch is a protected default branch
  PREFLIGHT_ERROR   2  Usage or preflight error
  SCRIPT_FAILURE    1  Unhandled error
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote)
      [[ $# -ge 2 ]] || { print_error "Missing value for --remote"; quit_by_code 2; }
      remote_name="$2"
      remote_was_explicit=1
      shift 2
      ;;
    --branch)
      [[ $# -ge 2 ]] || { print_error "Missing value for --branch"; quit_by_code 2; }
      branch_name="$2"
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

if [[ -z "${branch_name}" ]]; then
  branch_name="$(current_branch)"
fi

if [[ "${branch_name}" == "HEAD" ]]; then
  print_error "Detached HEAD: check out the pull request branch before pushing."
  quit_by_code 2
fi

if is_default_branch "${branch_name}"; then
  print_error "Refusing to push from ${branch_name}; a pull request head must be a feature branch."
  quit_by_code 5
fi

if ! git show-ref --verify --quiet "refs/heads/${branch_name}"; then
  print_error "Local branch not found: ${branch_name}"
  quit_by_code 2
fi

printf 'BRANCH=%s\n' "${branch_name}"

if upstream_ref="$(git rev-parse --abbrev-ref --symbolic-full-name "${branch_name}@{u}" 2>/dev/null)"; then
  upstream_remote="${upstream_ref%%/*}"
  upstream_branch="${upstream_ref#*/}"

  if [[ "${remote_was_explicit}" -eq 1 && "${upstream_remote}" != "${remote_name}" ]]; then
    print_error "Configured upstream remote '${upstream_remote}' does not match --remote '${remote_name}'."
    printf 'Please either rerun the command with --remote %s or update the branch upstream before continuing.\n' "${upstream_remote}" >&2
    quit_by_code 2
  fi

  git fetch --quiet "${upstream_remote}" "${upstream_branch}" 2>/dev/null || true

  ahead_count="$(git rev-list --count "${upstream_ref}..${branch_name}")"
  behind_count="$(git rev-list --count "${branch_name}..${upstream_ref}")"

  printf 'UPSTREAM=%s\n' "${upstream_ref}"
  printf 'AHEAD=%s\n' "${ahead_count}"
  printf 'BEHIND=%s\n' "${behind_count}"

  if [[ "${behind_count}" -gt 0 && "${ahead_count}" -gt 0 ]]; then
    print_error "Local branch has diverged from its upstream; the pull request head would not fast-forward."
    printf 'Merge the upstream branch into the local branch:\n' >&2
    printf '  git pull %s %s\n' "${upstream_remote}" "${upstream_branch}" >&2
    printf 'Resolve any conflicts, commit the merge, and rerun. Never force-push here.\n' >&2
    quit_by_code 3
  fi

  if [[ "${behind_count}" -gt 0 ]]; then
    print_error "Local branch is behind its upstream; the pull request head would not fast-forward."
    printf 'Reconcile the branch first, then rerun:\n' >&2
    printf '  git pull --ff-only %s %s\n' "${upstream_remote}" "${upstream_branch}" >&2
    printf 'If the branches diverged, merge the upstream branch instead. Never force-push here.\n' >&2
    quit_by_code 3
  fi

  if [[ "${ahead_count}" -eq 0 ]]; then
    printf 'ACTION=none\n'
    quit_by_code 0
  fi

  printf 'ACTION=push\n'
  if push_output="$(git push "${upstream_remote}" "refs/heads/${branch_name}:refs/heads/${upstream_branch}" 2>&1)"; then
    printf '%s\n' "${push_output}"
    quit_by_code 0
  fi

  print_error "Git push failed. Check Git credentials and remote permissions."
  printf '%s\n' "${push_output}" >&2
  quit_by_code 4
fi

if ! git remote get-url "${remote_name}" >/dev/null 2>&1; then
  print_error "Remote not found: ${remote_name}"
  quit_by_code 2
fi

printf 'UPSTREAM=%s/%s\n' "${remote_name}" "${branch_name}"
printf 'ACTION=push-with-upstream\n'

if [[ "${branch_name}" == "$(current_branch)" ]]; then
  push_command=(git push -u "${remote_name}" "${branch_name}")
else
  # Do not change the checked-out branch's upstream when --branch selects a
  # different local branch. The explicit refspec still creates that remote ref.
  push_command=(git push "${remote_name}" "refs/heads/${branch_name}:refs/heads/${branch_name}")
fi

if push_output="$("${push_command[@]}" 2>&1)"; then
  printf '%s\n' "${push_output}"
  quit_by_code 0
fi

print_error "Git push failed. Check Git credentials and remote permissions."
printf '%s\n' "${push_output}" >&2
quit_by_code 4
