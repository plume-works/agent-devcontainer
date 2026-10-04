#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${script_dir}/__common.sh"

RESULT_CODES+=("3=NO_CHANGES")

base_ref="origin/main"
commit_range=""
include_patch=1

usage() {
  show_help_header "Review working tree and branch changes for the pr-gen-description skill."
  cat <<'EOF'

Usage:
  review-git-changes.sh [--base-ref <ref>] [--range <range>] [--stat-only]

Options:
  --base-ref <ref>   Base ref used to find the merge base for the default
                     comparison range. Default: origin/main
  --range <range>    Explicit git revision range, for example main..HEAD.
  --stat-only        Skip the full patch and print summary sections only.
  -h, --help         Show this help text.

Output:
  RESULT, as the last line.
  Before it, the report sections the skill reads: '== Branch ==',
  '== Status ==', '== Diff Stat (<range>) ==', '== Commit Log (<range>) ==',
  plus '== Working Tree Diff ==' and '== Commit Range Diff (<range>) ==' unless
  --stat-only was passed.

Results (RESULT / exit code):
  SUCCESS          0  The change report was printed
  NO_CHANGES       3  Nothing to describe: no working tree changes and no
                      commits in the range. The report is still printed
  PREFLIGHT_ERROR  2  Usage or preflight error (not a repo, no commits,
                      unknown base ref or range, unrelated histories)
  SCRIPT_FAILURE   1  Unhandled error

Examples:
  agent-code/review-git-changes.sh
  agent-code/review-git-changes.sh --base-ref upstream/main
  agent-code/review-git-changes.sh --range origin/main..HEAD --stat-only
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-ref)
      [[ $# -ge 2 ]] || { print_error "Missing value for --base-ref"; quit_by_code 2; }
      base_ref="$2"
      shift 2
      ;;
    --range)
      [[ $# -ge 2 ]] || { print_error "Missing value for --range"; quit_by_code 2; }
      commit_range="$2"
      shift 2
      ;;
    --stat-only)
      include_patch=0
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

if ! git rev-parse --verify --quiet HEAD >/dev/null; then
  print_error "Repository does not contain any commits yet."
  quit_by_code 2
fi

if [[ -z "${commit_range}" ]]; then
  if ! git rev-parse --verify --quiet "${base_ref}" >/dev/null; then
    print_error "Base ref not found: ${base_ref}"
    quit_by_code 2
  fi

  if ! merge_base="$(git merge-base "${base_ref}" HEAD)"; then
    print_error "Could not determine merge base between ${base_ref} and HEAD."
    print_error "Ensure both refs exist and have related commit histories."
    quit_by_code 2
  fi
  commit_range="${merge_base}..HEAD"
else
  # Resolve a caller-supplied range before any git command consumes it.
  # Unresolved, the first `git diff` would die at 128 and report
  # UNKNOWN_CODE_128 instead of a preflight error the caller can act on.
  if ! git rev-list --max-count=1 "${commit_range}" >/dev/null 2>&1; then
    print_error "Commit range does not resolve: ${commit_range}"
    quit_by_code 2
  fi
fi

printf '== Branch ==\n'
printf '%s\n\n' "$(current_branch)"

printf '== Status ==\n'
git status --short --branch
printf '\n'

printf '== Diff Stat (%s) ==\n' "${commit_range}"
git --no-pager diff --stat "${commit_range}"
printf '\n'

if [[ "${include_patch}" -eq 1 ]]; then
  printf '== Working Tree Diff ==\n'
  git --no-pager diff
  printf '\n'

  printf '== Commit Range Diff (%s) ==\n' "${commit_range}"
  git --no-pager diff "${commit_range}"
  printf '\n'
fi

printf '== Commit Log (%s) ==\n' "${commit_range}"
git --no-pager log --oneline "${commit_range}"

if [[ -z "$(git status --porcelain)" ]] && [[ -z "$(git rev-list --max-count=1 "${commit_range}")" ]]; then
  printf 'NOTE: No working tree changes and no commits detected in %s.\n' "${commit_range}" >&2
  quit_by_code 3
fi

quit_by_code 0
