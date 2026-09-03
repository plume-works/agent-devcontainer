#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${script_dir}/__common.sh"

RESULT_CODES+=("3=GH_UNAVAILABLE" "4=ISSUE_NOT_FOUND" "5=ALREADY_CLOSED")

issue_ref=""
issue_repo=""
issue_number=""
repo_root=""
plan_path=""
comment_text=""

usage() {
  show_help_header "Close a GitHub issue that a filed plan now tracks, linking the plan in a comment."
  cat <<'HELP'

Usage:
  close-issue.sh --issue <issue> --plan <path> [--comment <text>]

Options:
  --issue <issue>    An issue URL, OWNER/REPO#N, #N, or N. The bare forms
                     resolve against the repository in the current directory.
  --plan <path>      Repo-relative path of the plan document; it must exist.
  --comment <text>   Replace the default closing comment, which names the
                     plan path, the current branch, and the repository.
  -h, --help         Show this help text.

Output (key=value lines):
  RESULT, ISSUE_REPO, ISSUE_NUMBER, ISSUE_URL, ISSUE_STATE

Results (RESULT / exit code):
  SUCCESS          0  The comment was posted and the issue is now closed
  ALREADY_CLOSED   5  The issue was already closed; nothing was changed
  ISSUE_NOT_FOUND  4  The repository has no issue with that number
  GH_UNAVAILABLE   3  gh is missing, unauthenticated, or its API call failed
  PREFLIGHT_ERROR  2  Usage or preflight error (not a repo, missing plan file)
  SCRIPT_FAILURE   1  Unhandled error
  SIGNAL_HUP     129  Interrupted by HUP
  SIGNAL_INT     130  Interrupted by INT
  SIGNAL_TERM    143  Interrupted by TERM
HELP
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue)
      [[ $# -ge 2 ]] || { print_error "Missing value for --issue"; quit_by_code 2; }
      issue_ref="$2"
      shift 2
      ;;
    --plan)
      [[ $# -ge 2 ]] || { print_error "Missing value for --plan"; quit_by_code 2; }
      plan_path="$2"
      shift 2
      ;;
    --comment)
      [[ $# -ge 2 ]] || { print_error "Missing value for --comment"; quit_by_code 2; }
      comment_text="$2"
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

[[ -n "${issue_ref}" ]] || { print_error "Missing --issue."; usage >&2; quit_by_code 2; }
[[ -n "${plan_path}" ]] || { print_error "Missing --plan."; usage >&2; quit_by_code 2; }

if ! parse_issue_ref "${issue_ref}"; then
  print_error "Unrecognized issue reference: ${issue_ref} (use a URL, OWNER/REPO#N, #N, or N)."
  quit_by_code 2
fi

require_git_repo

if [[ ! -f "${repo_root}/${plan_path}" ]]; then
  print_error "Plan file not found: ${plan_path} (relative to ${repo_root})."
  quit_by_code 2
fi

require_gh || quit_by_code 3

current_repo=""
if [[ -z "${issue_repo}" || -z "${comment_text}" ]]; then
  current_repo="$(resolve_current_repo)" || {
    print_error "Could not resolve the current repository; pass OWNER/REPO#N or an issue URL."
    quit_by_code 3
  }
fi
[[ -n "${issue_repo}" ]] || issue_repo="${current_repo}"

if [[ -z "${comment_text}" ]]; then
  branch_name="$(git rev-parse --abbrev-ref HEAD)"
  comment_text="Planned in \`${plan_path}\` on branch \`${branch_name}\` of ${current_repo}. Closing; the plan tracks the work from here."
fi

state_output=""
if ! state_output="$(gh issue view "${issue_number}" --repo "${issue_repo}" \
  --json url,state --template 'ISSUE_URL={{.url}}
ISSUE_STATE={{.state}}' 2>&1)"; then
  printf '%s\n' "${state_output}" >&2
  if gh_output_says_not_found "${state_output}"; then
    print_error "Issue ${issue_repo}#${issue_number} does not exist."
    quit_by_code 4
  fi
  print_error "gh issue view failed for ${issue_repo}#${issue_number}."
  quit_by_code 3
fi

issue_url="$(sed -n 's/^ISSUE_URL=//p' <<<"${state_output}")"
issue_state="$(sed -n 's/^ISSUE_STATE=//p' <<<"${state_output}")"

printf 'ISSUE_REPO=%s\n' "${issue_repo}"
printf 'ISSUE_NUMBER=%s\n' "${issue_number}"
printf 'ISSUE_URL=%s\n' "${issue_url}"

if [[ "${issue_state}" == "CLOSED" ]]; then
  printf 'ISSUE_STATE=CLOSED\n'
  printf 'Issue %s#%s is already closed; no comment posted.\n' "${issue_repo}" "${issue_number}" >&2
  quit_by_code 5
fi

if ! gh issue close "${issue_number}" --repo "${issue_repo}" --comment "${comment_text}" >&2; then
  print_error "gh issue close failed for ${issue_repo}#${issue_number}."
  quit_by_code 3
fi

printf 'ISSUE_STATE=CLOSED\n'
quit_by_code 0
