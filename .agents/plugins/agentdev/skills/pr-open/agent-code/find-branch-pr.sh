#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${script_dir}/__common.sh"

RESULT_CODES+=("3=NO_PR_FOUND" "4=MULTIPLE_PRS" "5=PROTECTED_BRANCH" "6=GH_UNAVAILABLE")

branch_name=""
state_filter="open"

usage() {
  show_help_header "Find the pull request whose head is the current branch."
  cat <<'EOF'

Usage:
  find-branch-pr.sh [--branch <name>] [--state open|all]

Options:
  --branch <name>    Head branch to look up. Default: current branch
  --state <state>    PR state filter: open (default) or all
  -h, --help         Show this help text.

Output (key=value lines):
  RESULT, HEAD_BRANCH, PR_FOUND
  On a match also: PR_NUMBER, PR_URL, PR_STATE, PR_IS_DRAFT, PR_BASE, PR_HEAD,
  PR_TITLE

HEAD_BRANCH is the pull request head to look up and to create against. It is
the configured upstream branch name when the local branch tracks a differently
named ref (local 'review-31' tracking 'fork/feature' resolves to 'feature'),
and the local branch name otherwise.

Results (RESULT / exit code):
  SUCCESS           0  Exactly one matching pull request was found
  NO_PR_FOUND       3  No matching pull request exists (the branch needs one)
  MULTIPLE_PRS      4  Multiple matching pull requests exist
  PROTECTED_BRANCH  5  Branch is a protected default branch
  GH_UNAVAILABLE    6  gh is missing, unauthenticated, or its API call failed
  PREFLIGHT_ERROR   2  Usage or preflight error (not a repo, detached HEAD)
  SCRIPT_FAILURE    1  Unhandled error

HEAD_BRANCH is printed before the gh checks, so it is available on GH_UNAVAILABLE
for a caller that falls back to a GitHub MCP server for the lookup.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch)
      [[ $# -ge 2 ]] || { print_error "Missing value for --branch"; quit_by_code 2; }
      branch_name="$2"
      shift 2
      ;;
    --state)
      [[ $# -ge 2 ]] || { print_error "Missing value for --state"; quit_by_code 2; }
      state_filter="$2"
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

case "${state_filter}" in
  open|all) ;;
  *)
    print_error "Unsupported --state value: ${state_filter} (use open or all)"
    quit_by_code 2
    ;;
esac

require_git_repo

if [[ -z "${branch_name}" ]]; then
  branch_name="$(current_branch)"
fi

if [[ "${branch_name}" == "HEAD" ]]; then
  print_error "Detached HEAD: check out the pull request branch before looking up its pull request."
  quit_by_code 2
fi

if is_default_branch "${branch_name}"; then
  print_error "Branch ${branch_name} is a protected default branch; a pull request head must be a feature branch."
  quit_by_code 5
fi

# The pull request head is the remote branch, which push-branch.sh writes to.
# It only matches the local branch name when the branch has no upstream or the
# upstream carries the same name.
head_branch="${branch_name}"
if upstream_ref="$(git rev-parse --abbrev-ref --symbolic-full-name "${branch_name}@{u}" 2>/dev/null)"; then
  head_branch="${upstream_ref#*/}"
fi

if [[ "${head_branch}" != "${branch_name}" ]] && is_default_branch "${head_branch}"; then
  print_error "Branch ${branch_name} tracks ${upstream_ref}; a pull request head must be a feature branch."
  quit_by_code 5
fi

printf 'HEAD_BRANCH=%s\n' "${head_branch}"

# GH_UNAVAILABLE, not PREFLIGHT_ERROR: these are the conditions the skill's
# GitHub MCP fallback exists for, so the caller must be able to tell them apart
# from a preflight error that no fallback can rescue.
if ! command -v gh >/dev/null 2>&1; then
  print_error "GitHub CLI (gh) is not installed."
  quit_by_code 6
fi

if ! gh auth status >/dev/null 2>&1; then
  print_error "GitHub CLI is not authenticated. Run 'gh auth login' and retry."
  quit_by_code 6
fi

# A Go template keeps this dependent on `gh` alone, with no jq requirement.
# Each match starts with a PR_RECORD marker line so matches can be counted.
pr_template='{{range .}}PR_RECORD
PR_NUMBER={{.number}}
PR_URL={{.url}}
PR_STATE={{.state}}
PR_IS_DRAFT={{.isDraft}}
PR_BASE={{.baseRefName}}
PR_HEAD={{.headRefName}}
PR_TITLE={{.title}}
{{end}}'

pr_output=""
if ! pr_output="$(gh pr list \
  --head "${head_branch}" \
  --state "${state_filter}" \
  --json number,url,state,isDraft,baseRefName,headRefName,title \
  --template "${pr_template}" \
  2>&1)"; then
  # Also GH_UNAVAILABLE: a call that failed on scope, network, or rate limit
  # leaves gh just as unusable as a missing one, and the MCP fallback rescues it.
  print_error "gh pr list failed for head branch ${head_branch}."
  printf '%s\n' "${pr_output}" >&2
  quit_by_code 6
fi

pr_count="$(printf '%s\n' "${pr_output}" | grep -c '^PR_RECORD$' || true)"

if [[ "${pr_count}" -eq 0 ]]; then
  printf 'PR_FOUND=false\n'
  printf 'No %s pull request found with head branch %s; the branch needs a new pull request.\n' \
    "${state_filter}" "${head_branch}" >&2
  quit_by_code 3
fi

if [[ "${pr_count}" -gt 1 ]]; then
  print_error "Found ${pr_count} pull requests with head branch '${head_branch}'; refusing to guess which one to update."
  printf '%s\n' "${pr_output}" >&2
  quit_by_code 4
fi

printf 'PR_FOUND=true\n'
printf '%s\n' "${pr_output}" | grep -v '^PR_RECORD$' | grep -v '^$'

quit_by_code 0
