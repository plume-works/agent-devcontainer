#!/usr/bin/env bash
set -euo pipefail

# Stands in for a build step that leaves its output untracked in the worktree.
root="$(git rev-parse --show-toplevel)"
cp "${root}/e2e/hello.txt" "${root}/e2e/hello.bundle"
echo "bundled"
