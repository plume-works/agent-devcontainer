---
type: bug
description: The agentdev runtime package declares pyyaml and setuptools as ranges, so an image build can install a different version of each without a change in the repository.
stage: pending
severity: low
sources:
- resource: py_packages/agentdev_runtime/pyproject.toml
- resource: docs/knowledge/data/findings/spec-usefulness-audit.md
- resource: docs/spec-audit/requirements.jsonl
---

# Bug: the runtime package installs two dependencies from a version range

## Symptom

The images install `agentdev-runtime` as a uv tool, and its dependencies must be
pinned. Two of them are not: `pyyaml>=6.0` and `setuptools<85`. Two image builds
from the same commit can install different versions of these packages.

## Reproduction

1. Read `py_packages/agentdev_runtime/pyproject.toml#project.dependencies`.
2. `supervisor` and `json5` use `==`. `pyyaml` uses `>=` and `setuptools` uses
   `<`.
3. `uv tool install` on the package directory does not read
   `py_packages/agentdev_runtime/uv.lock`, so the lock file does not pin them.

## Root cause

`py_packages/agentdev_runtime/pyproject.toml#project.dependencies` declares
`"pyyaml>=6.0"` and `"setuptools<85"`. The ceiling on `setuptools` keeps
`pkg_resources` for `supervisor`, but it does not pin one version.
