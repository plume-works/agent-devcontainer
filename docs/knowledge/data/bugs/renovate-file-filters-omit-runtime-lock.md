---
type: bug
description: postUpgradeTasks.fileFilters in .github/renovate.json lists the root uv.lock but not py_packages/agentdev_runtime/uv.lock, so Renovate drops a post-upgrade change to that file.
stage: pending
severity: low
sources:
- resource: .github/renovate.json
- resource: scripts/renovate-post-upgrade.py
- resource: docs/knowledge/data/findings/spec-usefulness-audit.md
- resource: docs/spec-audit/requirements.jsonl
---

# Bug: Renovate's post-upgrade file filters omit the runtime package's lock file

## Symptom

The post-upgrade task's `fileFilters` must match each path that a Renovate
manager in this repository edits. Renovate keeps post-upgrade output only where
it matches them. `py_packages/agentdev_runtime/uv.lock` is next to a `pep621`
manifest, and lock file maintenance relocks it, but no filter matches it. A
change that the post-upgrade task makes to this file is not in Renovate's
commit.

## Reproduction

1. Read `.github/renovate.json#postUpgradeTasks.fileFilters`.
2. It holds `uv.lock` and `py_packages/*/pyproject.toml`, and no pattern that
   matches `py_packages/agentdev_runtime/uv.lock`.

## Root cause

`.github/renovate.json#postUpgradeTasks.fileFilters` lists the root `uv.lock`
only.
