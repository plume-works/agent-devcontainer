---
type: bug
description: Two local pre-commit hooks omit the pre-merge-commit stage, so a merge that commits without a conflict does not run them.
stage: pending
severity: low
sources:
- resource: .pre-commit-config.yaml
- resource: docs/knowledge/data/findings/spec-usefulness-audit.md
- resource: docs/spec-audit/requirements.jsonl
---

# Bug: a merge commit skips `end-of-file-fixer` and `trailing-whitespace`

## Symptom

Each commit path, merges included, must run the same pre-commit hooks. A merge
that commits on its own runs the `pre-merge-commit` stage, and that stage does
not run `end-of-file-fixer` or `trailing-whitespace`. A merge can thus put a
file with trailing whitespace or no final newline on a branch.

## Reproduction

1. On a branch, commit a file with trailing whitespace while the two hooks are
   skipped, for example with `SKIP=trailing-whitespace`.
2. Merge that branch into a second branch with `git merge --no-ff`, with no
   conflict.
3. The merge commit completes, and the `pre-merge-commit` output does not show
   either hook.

## Root cause

`.pre-commit-config.yaml#default_stages` includes `pre-merge-commit`, but the
two hooks override it: `id: end-of-file-fixer` and `id: trailing-whitespace`
each set `stages: [pre-commit, pre-push, manual]`.
