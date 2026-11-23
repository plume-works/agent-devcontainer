---
type: bug
description: The agentdev runtime package declares pyyaml as a range. Thus an image build can install a different version when the repository does not change.
stage: pending
severity: low
sources:
- resource: py_packages/agentdev_runtime/pyproject.toml
- resource: docs/knowledge/data/findings/spec-usefulness-audit.md
---

# Bug: the runtime package installs a dependency from a version range

## Symptom

The image installs `agentdev-runtime` as a uv tool, and its dependencies must be
pinned. One is not: `pyyaml>=6.0`. Two image builds from the same commit can
install different versions of it.

## Reproduction

1. Read `py_packages/agentdev_runtime/pyproject.toml#project.dependencies`.
2. `json5` uses `==`. `pyyaml` uses `>=`.
3. `uv tool install` on the package directory does not read
   `py_packages/agentdev_runtime/uv.lock`, so the lock file does not pin them.

## Root cause

`py_packages/agentdev_runtime/pyproject.toml#project.dependencies` declares
`"pyyaml>=6.0"`, a range rather than one version.
