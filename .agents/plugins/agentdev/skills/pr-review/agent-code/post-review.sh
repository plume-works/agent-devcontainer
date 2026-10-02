#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${script_dir}/__common.sh"

RESULT_CODES+=("3=GH_CALL_FAILED")

repo=""
pr_number=""
event=""
summary_file=""
comments_file=""

usage() {
  cat <<'EOF'
Create and submit a GitHub PR review with all inline comments in a
single atomic call -- no pending-review/add-comment/submit dance.

Usage:
  post-review.sh --pr <PR_NUMBER> --event <COMMENT|APPROVE|REQUEST_CHANGES> \
    --summary-file <path> [--comments-file <path>] [--repo <owner/name>]

--summary-file must be a plain file (write it with the Write tool
first) containing only the short overall summary -- no per-finding
detail, since findings live in the inline comments.

--comments-file, if given, must be a plain JSON file (write it with
the Write tool first) containing an array of findings, e.g.:
  [
    {"path": "src/foo.py", "line": 42, "side": "RIGHT", "body": "..."},
    {"path": "src/bar.cpp", "line": 7, "side": "RIGHT", "body": "..."}
  ]
Omit --comments-file (or pass a file containing []) when there are no
validated findings to attach.

Output (key=value lines):
  RESULT
  On success the created review object is printed before the RESULT
  line, verbatim as the GitHub API returned it.

Results (RESULT / exit code):
  SUCCESS          0  The review was created and submitted
  GH_CALL_FAILED   3  A gh API call failed (repo/PR lookup, or the review POST)
  PREFLIGHT_ERROR  2  Usage error, a missing or malformed input file, or gh/jq
                      missing or unauthenticated
  SCRIPT_FAILURE   1  Unhandled error
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pr) require_arg "--pr" "${2:-}"; pr_number="$2"; shift 2 ;;
    --event) require_arg "--event" "${2:-}"; event="$2"; shift 2 ;;
    --summary-file) require_arg "--summary-file" "${2:-}"; summary_file="$2"; shift 2 ;;
    --comments-file) require_arg "--comments-file" "${2:-}"; comments_file="$2"; shift 2 ;;
    --repo) require_arg "--repo" "${2:-}"; repo="$2"; shift 2 ;;
    -h|--help) usage; quit_by_code 0 ;;
    *) print_error "Unknown argument: $1"; usage >&2; quit_by_code 2 ;;
  esac
done

require_arg "--pr" "${pr_number}"
require_arg "--event" "${event}"
require_arg "--summary-file" "${summary_file}"
require_body_file "${summary_file}"

case "${event}" in
  COMMENT|APPROVE|REQUEST_CHANGES) ;;
  *) print_error "Invalid --event: ${event} (expected COMMENT, APPROVE, or REQUEST_CHANGES)"; quit_by_code 2 ;;
esac

require_gh
require_jq

if [[ -n "${comments_file}" ]]; then
  require_body_file "${comments_file}"
else
  mkdir -p ./.tmp
  comments_file="./.tmp/post-review-empty-comments.json"
  printf '[]' >"${comments_file}"
fi

if [[ -z "${repo}" ]]; then
  if ! repo="$(resolve_repo)"; then
    print_error "gh repo view failed; could not resolve the current repository. Pass --repo <owner/name>."
    quit_by_code 3
  fi
fi

if ! commit_id="$(gh pr view "${pr_number}" --repo "${repo}" --json headRefOid -q .headRefOid)"; then
  print_error "gh pr view failed for pull request ${pr_number} in ${repo}."
  quit_by_code 3
fi

if ! payload="$(jq -n \
  --arg commit_id "${commit_id}" \
  --arg event "${event}" \
  --rawfile body "${summary_file}" \
  --slurpfile comments_arr "${comments_file}" \
  '{commit_id: $commit_id, event: $event, body: $body, comments: $comments_arr[0]}')"; then
  print_error "Could not build the review payload; check that ${comments_file} holds a valid JSON array."
  quit_by_code 2
fi

if ! review_response="$(printf '%s' "${payload}" | gh api "repos/${repo}/pulls/${pr_number}/reviews" --method POST --input -)"; then
  print_error "gh api review POST failed for pull request ${pr_number} in ${repo}."
  printf 'If the error names a comment that cannot be placed inline, drop that entry from the comments file, rerun, and post it as a normal PR comment.\n' >&2
  quit_by_code 3
fi

printf '%s\n' "${review_response}"

quit_by_code 0
