#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

print_error() {
  printf 'ERROR: %s\n' "$*" >&2
}

# shellcheck source=/dev/null
source "${script_dir}/../../../bin/result-codes.sh"
# shellcheck source=/dev/null
source "${script_dir}/../../../bin/git-default-branch.sh"

RESULT_CODES+=("3=PROTECTED_BRANCH" "4=COMMIT_FAILED" "5=DEFAULT_UNKNOWN")

remote_name="origin"

usage() {
  cat <<'HELP'
Create a commit, refusing on the repository's default branch.

Usage:
  git-commit.sh [--remote <name>] -- <git commit arguments>

Options:
  --remote <name>  Remote whose default branch is protected. Default: origin
  -h, --help       Show this help text.

Protected: main, master, and the branch refs/remotes/<remote>/HEAD names (or,
when that is unset, the default branch gh reports for the remote's URL). When
the remote exists but neither source names its default branch, the commit is
refused; when the remote is not configured, only main and master are protected.

Output:
  The output of git commit, then key=value lines:
  BRANCH, GIT_EXIT_CODE (only when git commit ran), RESULT
  GIT_EXIT_CODE is git commit's own status; the script's exit code is RESULT's.

Results (RESULT / exit code):
  SUCCESS           0  The commit was created
  PROTECTED_BRANCH  3  The current branch is a default branch; git commit did not run
  COMMIT_FAILED     4  git commit ran and failed (nothing staged, hook failure)
  DEFAULT_UNKNOWN   5  The remote exists but its default branch could not be
                       determined; git commit did not run
  PREFLIGHT_ERROR   2  Bad usage, not a repository, or a detached HEAD
  SCRIPT_FAILURE    1  Unhandled error
  SIGNAL_HUP      129  Interrupted by HUP
  SIGNAL_INT      130  Interrupted by INT
  SIGNAL_TERM     143  Interrupted by TERM

Examples:
  agent-code/git-commit.sh -- -m "fix(serial): handle reconnect timeout"
  agent-code/git-commit.sh -- -F .tmp/commit-message.txt
HELP
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote)
      [[ $# -ge 2 ]] || { print_error "Missing value for --remote"; quit_by_code 2; }
      remote_name="$2"
      shift 2
      ;;
    -h|--help)
      usage
      quit_by_code 0
      ;;
    --)
      shift
      break
      ;;
    *)
      print_error "Unknown argument: $1 (pass git commit arguments after --)"
      usage >&2
      quit_by_code 2
      ;;
  esac
done

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  print_error "This script must be run inside a Git repository."
  quit_by_code 2
fi

if ! branch_name="$(git symbolic-ref --quiet --short HEAD)"; then
  print_error "HEAD is detached; commit on a feature branch instead."
  quit_by_code 2
fi
printf 'BRANCH=%s\n' "${branch_name}"

protected=0
if is_default_branch "${branch_name}"; then
  protected=1
elif default_branch="$(remote_default_branch "${remote_name}")"; then
  [[ "${branch_name}" != "${default_branch}" ]] || protected=1
elif git remote get-url "${remote_name}" >/dev/null 2>&1; then
  print_error "Cannot tell whether '${branch_name}' is the default branch of '${remote_name}'."
  print_error "Run: git remote set-head ${remote_name} --auto, or authenticate gh (gh auth login)."
  quit_by_code 5
fi
if [[ "${protected}" -eq 1 ]]; then
  print_error "Refusing to commit on the default branch '${branch_name}'."
  print_error "Create a work branch with /agentdev:git-new-branch; it carries uncommitted changes."
  quit_by_code 3
fi

status=0
git commit "$@" || status=$?

printf '\nGIT_EXIT_CODE=%s\n' "${status}"
if [[ "${status}" -ne 0 ]]; then
  quit_by_code 4
fi
quit_by_code 0
