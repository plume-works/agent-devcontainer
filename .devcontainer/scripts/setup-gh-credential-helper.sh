#!/usr/bin/env bash
# Lets HTTPS git push/fetch reuse gh's login. Without a helper, git waits at a
# credential prompt that headless agents cannot answer. A helper already
# configured for github.com wins and is left untouched.

set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "gh is not installed; skipping git credential helper setup."
  exit 0
fi

if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  echo "gh is not authenticated to github.com; skipping git credential helper setup."
  exit 0
fi

if existing="$(git config --get-urlmatch credential.helper https://github.com)" &&
  [[ -n "$existing" ]]; then
  echo "A git credential helper for github.com is already configured; leaving it unchanged."
  exit 0
fi

gh auth setup-git
echo "Configured gh as the git credential helper."
