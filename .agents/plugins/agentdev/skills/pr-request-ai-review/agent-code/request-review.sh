#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

pr_number=""
rationale=""
repo=""

print_error() {
  printf 'ERROR: %s\n' "$*" >&2
}

# shellcheck source=/dev/null
source "${script_dir}/../../../bin/result-codes.sh"

RESULT_CODES+=("3=ALREADY_REVIEWED" "4=ALREADY_REQUESTED" "5=PR_NOT_OPEN" "6=GH_UNAVAILABLE")

usage() {
  cat <<'EOF'
Request an AI review of a pull request's head commit by toggling the author's
assignment, at most once per head.

Usage:
  request-review.sh --pr <number> [--rationale <one line>] [--repo <owner/repo>]

Options:
  --pr <number>          Pull request to request a review for. Required.
  --rationale <line>     One line naming what the reviewer has not seen yet,
                         posted as a plain comment after the toggle.
  --repo <owner/repo>    Repository. Default: the current checkout's repository.
  -h, --help             Show this help text.

An assigned author is removed and added back; an unassigned one is added and
removed, so the assignees end as they were found. The request is refused when
an accepted AI review already names the head, or a Claude PR Review Responder
check on the head is queued, in progress, or completed other than skipped or
cancelled.

Output:
  RESULT is always the last line of stdout.
  PR_NUMBER    the pull request number
  HEAD_SHA     the head commit the decision applies to
  CHECK_URL    the responder check behind ALREADY_REQUESTED; empty otherwise
  COMMENT_URL  the posted rationale comment; empty when none was posted

Results (RESULT / exit code):
  SUCCESS            0  The author's assignment was toggled for the head
  ALREADY_REVIEWED   3  An accepted AI review's commit is the head
  ALREADY_REQUESTED  4  A Claude PR Review Responder check on the head counts as a request
  PR_NOT_OPEN        5  The pull request is closed, merged, or not found
  GH_UNAVAILABLE     6  gh is missing, unauthenticated, or an API call failed, the toggle too
  PREFLIGHT_ERROR    2  Missing --pr, unknown argument, multi-line rationale, no jq
  SCRIPT_FAILURE     1  Unhandled error
  SIGNAL_HUP       129  Interrupted by HUP
  SIGNAL_INT       130  Interrupted by INT
  SIGNAL_TERM      143  Interrupted by TERM
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pr)
      [[ $# -ge 2 ]] || { print_error "Missing value for --pr"; quit_by_code 2; }
      pr_number="$2"
      shift 2
      ;;
    --rationale)
      [[ $# -ge 2 ]] || { print_error "Missing value for --rationale"; quit_by_code 2; }
      rationale="$2"
      shift 2
      ;;
    --repo)
      [[ $# -ge 2 ]] || { print_error "Missing value for --repo"; quit_by_code 2; }
      repo="$2"
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

[[ "${pr_number}" =~ ^[0-9]+$ ]] || { print_error "--pr must be a pull request number."; quit_by_code 2; }
if [[ "${rationale}" == *$'\n'* || "${rationale}" == *$'\r'* ]]; then
  print_error "--rationale must be a single line."
  quit_by_code 2
fi
command -v jq >/dev/null 2>&1 || { print_error "jq not found on PATH."; quit_by_code 2; }
command -v gh >/dev/null 2>&1 || { print_error "gh not found on PATH."; quit_by_code 6; }

if [[ -z "${repo}" ]]; then
  if ! repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)" || [[ -z "${repo}" ]]; then
    print_error "Could not resolve the repository; pass --repo."
    quit_by_code 6
  fi
fi

# Collect every page of a list endpoint into one JSON array; `pages_filter`
# picks the items out of one page.
fetch_list() {
  local endpoint="$1"
  local pages_filter="$2"
  local pages

  pages="$(gh api --paginate "${endpoint}")" || return 1
  printf '%s' "${pages}" | jq -s "[.[] | ${pages_filter}]"
}

# Print the two URL keys, then exit with `code`.
finish() {
  local check_url="$1"
  local comment_url="$2"
  local code="$3"

  printf 'CHECK_URL=%s\n' "${check_url}"
  printf 'COMMENT_URL=%s\n' "${comment_url}"
  quit_by_code "${code}"
}

pr_status=0
pr_json="$(gh api "repos/${repo}/pulls/${pr_number}")" || pr_status=$?
if [[ "${pr_status}" -ne 0 ]]; then
  if [[ "$(printf '%s' "${pr_json}" | jq -r '.status? // empty' 2>/dev/null)" == "404" ]]; then
    print_error "Pull request ${repo}#${pr_number} was not found."
    quit_by_code 5
  fi
  print_error "Could not read pull request ${repo}#${pr_number}."
  quit_by_code 6
fi

printf 'PR_NUMBER=%s\n' "${pr_number}"
pr_state="$(printf '%s' "${pr_json}" | jq -r '.state')"
head_sha="$(printf '%s' "${pr_json}" | jq -r '.head.sha')"
author="$(printf '%s' "${pr_json}" | jq -r '.user.login')"
author_assigned="$(printf '%s' "${pr_json}" | jq --arg author "${author}" \
  'any(.assignees[]?; .login == $author)')"
printf 'HEAD_SHA=%s\n' "${head_sha}"
if [[ "${pr_state}" != "open" ]]; then
  print_error "Pull request ${repo}#${pr_number} is ${pr_state}."
  finish "" "" 5
fi

# Accepted reviewers and states: see spec/ai-review-gate. A reaction names no
# commit, so it cannot show that the head was reviewed.
reviews="$(fetch_list "repos/${repo}/pulls/${pr_number}/reviews" '.[]')" || {
  print_error "Could not read the reviews of ${repo}#${pr_number}."
  quit_by_code 6
}
reviewed="$(printf '%s' "${reviews}" | jq --arg head "${head_sha}" '
  any(.[];
    (.user.login | IN("claude[bot]", "github-actions[bot]"))
    and (.state | ascii_upcase | IN("APPROVED", "CHANGES_REQUESTED", "COMMENTED"))
    and .commit_id == $head)')"
[[ "${reviewed}" != "true" ]] || finish "" "" 3

# Which responder checks count as a request: see spec/ai-review-refresh.
runs="$(fetch_list "repos/${repo}/commits/${head_sha}/check-runs" '.check_runs[]')" || {
  print_error "Could not read the check runs of ${head_sha}."
  quit_by_code 6
}
existing_url="$(printf '%s' "${runs}" | jq -r '
  [.[]
    | select(.name == "Claude PR Review Responder")
    | select(.status != "completed" or (.conclusion | IN("skipped", "cancelled") | not))
  ] | first | .html_url // ""')"
[[ -z "${existing_url}" ]] || finish "${existing_url}" "" 4

# Adding fires pull_request/assigned; removing fires nothing the responder runs on.
assignees_endpoint="repos/${repo}/issues/${pr_number}/assignees"
if [[ "${author_assigned}" == "true" ]]; then
  first_call=DELETE
  second_call=POST
  unrestored="${author} is no longer assigned"
else
  first_call=POST
  second_call=DELETE
  unrestored="${author} is still assigned"
fi
if ! gh api -X "${first_call}" "${assignees_endpoint}" -f "assignees[]=${author}" >/dev/null; then
  print_error "Could not toggle ${author}'s assignment on ${repo}#${pr_number}."
  quit_by_code 6
fi
if ! gh api -X "${second_call}" "${assignees_endpoint}" -f "assignees[]=${author}" >/dev/null; then
  print_error "Could not restore the assignees of ${repo}#${pr_number}: ${unrestored}."
  quit_by_code 6
fi

comment_url=""
if [[ -n "${rationale}" ]]; then
  body="AI review requested for ${head_sha}: ${rationale}"
  if ! posted="$(gh api -X POST "repos/${repo}/issues/${pr_number}/comments" -f "body=${body}")"; then
    print_error "Requested the review but could not post the rationale on ${repo}#${pr_number}."
    quit_by_code 6
  fi
  comment_url="$(printf '%s' "${posted}" | jq -r '.html_url')"
fi
finish "" "${comment_url}" 0
