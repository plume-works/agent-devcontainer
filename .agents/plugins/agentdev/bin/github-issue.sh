#!/usr/bin/env bash

# Shared GitHub issue helpers for agentdev skill scripts. Sourced after
# result-codes.sh; every function returns non-zero instead of exiting so the
# caller decides which declared result the failure maps to.

# Parse an issue reference into issue_repo and issue_number. Accepts a GitHub
# issue URL, OWNER/REPO#N, #N, or N. issue_repo stays empty for the bare forms.
# shellcheck disable=SC2034  # assigned for the sourcing script
parse_issue_ref() {
  local ref="$1"
  issue_repo=""
  issue_number=""

  if [[ "${ref}" =~ ^https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/([0-9]+)/?(#.*)?$ ]]; then
    issue_repo="${BASH_REMATCH[1]}"
    issue_number="${BASH_REMATCH[2]}"
  elif [[ "${ref}" =~ ^([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#([0-9]+)$ ]]; then
    issue_repo="${BASH_REMATCH[1]}"
    issue_number="${BASH_REMATCH[2]}"
  elif [[ "${ref}" =~ ^#?([0-9]+)$ ]]; then
    issue_number="${BASH_REMATCH[1]}"
  else
    return 1
  fi
}

# Confirm gh is installed and authenticated; diagnostics go to stderr.
require_gh() {
  if ! command -v gh >/dev/null 2>&1; then
    printf 'ERROR: GitHub CLI (gh) is not installed.\n' >&2
    return 1
  fi
  if ! gh auth status >/dev/null 2>&1; then
    printf 'ERROR: GitHub CLI is not authenticated. Run '"'"'gh auth login'"'"' and retry.\n' >&2
    return 1
  fi
}

# Print OWNER/REPO for the repository in the current directory.
resolve_current_repo() {
  gh repo view --json nameWithOwner --jq .nameWithOwner
}

# True when gh's stderr says the issue does not exist rather than gh failing.
gh_output_says_not_found() {
  grep -qiE 'could not resolve to an issue|not found|no issue' <<<"$1"
}

# Close issue_repo#issue_number with a comment unless it is already closed,
# printing ISSUE_REPO, ISSUE_NUMBER, ISSUE_URL, and ISSUE_STATE lines. Returns
# 0 when closed, 3 when gh fails, 4 when the issue does not exist, and 5 when it
# was already closed — the result codes the closing scripts declare.
close_issue_with_comment() {
  local issue_repo="$1" issue_number="$2" comment_text="$3"
  local state_output issue_url issue_state

  if ! state_output="$(gh issue view "${issue_number}" --repo "${issue_repo}" \
    --json url,state --template 'ISSUE_URL={{.url}}
ISSUE_STATE={{.state}}' 2>&1)"; then
    printf '%s\n' "${state_output}" >&2
    if gh_output_says_not_found "${state_output}"; then
      printf 'ERROR: Issue %s#%s does not exist.\n' "${issue_repo}" "${issue_number}" >&2
      return 4
    fi
    printf 'ERROR: gh issue view failed for %s#%s.\n' "${issue_repo}" "${issue_number}" >&2
    return 3
  fi

  issue_url="$(sed -n 's/^ISSUE_URL=//p' <<<"${state_output}")"
  issue_state="$(sed -n 's/^ISSUE_STATE=//p' <<<"${state_output}")"

  printf 'ISSUE_REPO=%s\n' "${issue_repo}"
  printf 'ISSUE_NUMBER=%s\n' "${issue_number}"
  printf 'ISSUE_URL=%s\n' "${issue_url}"

  if [[ "${issue_state}" == "CLOSED" ]]; then
    printf 'ISSUE_STATE=CLOSED\n'
    printf 'Issue %s#%s is already closed; no comment posted.\n' "${issue_repo}" "${issue_number}" >&2
    return 5
  fi

  if ! gh issue close "${issue_number}" --repo "${issue_repo}" --comment "${comment_text}" >&2; then
    printf 'ERROR: gh issue close failed for %s#%s.\n' "${issue_repo}" "${issue_number}" >&2
    return 3
  fi

  printf 'ISSUE_STATE=CLOSED\n'
}
