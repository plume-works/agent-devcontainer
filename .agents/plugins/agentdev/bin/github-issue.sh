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
