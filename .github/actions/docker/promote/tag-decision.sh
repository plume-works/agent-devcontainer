#!/usr/bin/env bash
# Print "keep" when the tag names a descendant of GITHUB_SHA. If not, print "move".
# Usage: tag-decision.sh <revision label of the tag's image, may be empty>
set -euo pipefail

current="${1:-}"
# A tag that is already on a descendant of this commit stays there, thus a new run never moves it back.
if [[ -n "${current}" && "${current}" != "${GITHUB_SHA}" ]] \
  && git cat-file -e "${current}^{commit}" 2>/dev/null \
  && git merge-base --is-ancestor "${GITHUB_SHA}" "${current}"; then
  echo keep
else
  echo move
fi
