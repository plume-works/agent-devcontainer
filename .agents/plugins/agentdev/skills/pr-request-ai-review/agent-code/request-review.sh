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
Post an `@claude review` trigger for a pull request's head commit, at most once per head.

Usage:
  request-review.sh --pr <number> [--rationale <one line>] [--repo <owner/repo>]

Options:
  --pr <number>          Pull request to request a review for. Required.
  --rationale <line>     One line naming what the reviewer has not seen yet.
  --repo <owner/repo>    Repository. Default: the current checkout's repository.
  -h, --help             Show this help text.

The trigger is refused when an accepted AI review already names the head, or a
trigger for the head exists: one whose review-head marker names it, or an
unmarked one created after the head's earliest check suite.

Output:
  RESULT is always the last line of stdout.
  PR_NUMBER    the pull request number
  HEAD_SHA     the head commit the decision applies to
  COMMENT_URL  the posted or the existing trigger; empty for ALREADY_REVIEWED

Results (RESULT / exit code):
  SUCCESS            0  Trigger posted for the head
  ALREADY_REVIEWED   3  An accepted AI review's commit is the head
  ALREADY_REQUESTED  4  A trigger names the head, or an unmarked one postdates its arrival
  PR_NOT_OPEN        5  The pull request is closed, merged, or not found
  GH_UNAVAILABLE     6  gh is missing, unauthenticated, or its API call failed
  PREFLIGHT_ERROR    2  Missing --pr, unknown argument, multi-line rationale, no jq
  SCRIPT_FAILURE     1  Unhandled error
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
printf 'HEAD_SHA=%s\n' "${head_sha}"
if [[ "${pr_state}" != "open" ]]; then
  print_error "Pull request ${repo}#${pr_number} is ${pr_state}."
  printf 'COMMENT_URL=\n'
  quit_by_code 5
fi

# Accepted reviewers and states: see spec/ai-review-gate. A reaction names no
# commit, so it cannot show that the head was reviewed.
reviews="$(fetch_list "repos/${repo}/pulls/${pr_number}/reviews" '.[]')" || {
  print_error "Could not read the reviews of ${repo}#${pr_number}."
  quit_by_code 6
}
reviewed="$(printf '%s' "${reviews}" | jq --arg head "${head_sha}" '
  any(.[];
    (.user.login | IN("claude[bot]", "github-actions[bot]", "chatgpt-codex-connector[bot]"))
    and (.state | ascii_upcase | IN("APPROVED", "CHANGES_REQUESTED", "COMMENTED"))
    and .commit_id == $head)')"
if [[ "${reviewed}" == "true" ]]; then
  printf 'COMMENT_URL=\n'
  quit_by_code 3
fi

suites="$(fetch_list "repos/${repo}/commits/${head_sha}/check-suites" '.check_suites[]')" || {
  print_error "Could not read the check suites of ${head_sha}."
  quit_by_code 6
}
arrival="$(printf '%s' "${suites}" | jq -r '[.[].created_at] | min // ""')"

comments="$(fetch_list "repos/${repo}/issues/${pr_number}/comments" '.[]')" || {
  print_error "Could not read the comments of ${repo}#${pr_number}."
  quit_by_code 6
}
existing_url="$(printf '%s' "${comments}" | jq -r --arg head "${head_sha}" --arg arrival "${arrival}" '
  [.[]
    | select(.body | ascii_downcase | startswith("@claude review"))
    | ((.body | capture("<!-- review-head: (?<sha>[0-9A-Fa-f]+) -->")? | .sha) // null) as $marked
    | select(if $marked then $marked == $head
             else $arrival != "" and .created_at > $arrival end)
  ] | first | .html_url // ""')"
if [[ -n "${existing_url}" ]]; then
  printf 'COMMENT_URL=%s\n' "${existing_url}"
  quit_by_code 4
fi

body="@claude review"
[[ -z "${rationale}" ]] || body+=$'\n'"${rationale}"
body+=$'\n'"<!-- review-head: ${head_sha} -->"

if ! posted="$(gh api -X POST "repos/${repo}/issues/${pr_number}/comments" -f "body=${body}")"; then
  print_error "Could not post the trigger on ${repo}#${pr_number}."
  quit_by_code 6
fi
printf 'COMMENT_URL=%s\n' "$(printf '%s' "${posted}" | jq -r '.html_url')"
quit_by_code 0
