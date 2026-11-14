---
type: bug
description: In the deploy profile, the runtime configures the git credential helper only before a clone. Thus a start that reuses a mounted checkout cannot use the injected token for HTTPS git.
stage: pending
severity: medium
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/workspace.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/git.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: docs/knowledge/data/findings/spec-usefulness-audit.md
- resource: docs/spec-audit/requirements.jsonl
---

# Bug: a deploy runtime that reuses a checkout does not configure the git credential helper

## Symptom

The standalone runtime must use the injected token for each GitHub HTTPS
operation, whether it clones the workspace or uses a checkout that exists. When
the start uses a bind-mounted checkout, git has no credential helper, and
`git fetch` or `git push` over HTTPS asks for credentials or fails.

## Reproduction

1. Start the deploy image with a GitHub token and a bind-mounted checkout whose
   remote is an HTTPS GitHub URL.
2. The start log shows "reusing checkout".
3. In the container, `git config --get-all credential.https://github.com.helper`
   shows no helper, and `git fetch` cannot authenticate.

## Root cause

`py_packages/agentdev_runtime/agentdev_runtime/git.py::credential_helper` runs
in the deploy profile only from
`py_packages/agentdev_runtime/agentdev_runtime/workspace.py::Workspace.clone`.
The path that reuses a checkout does not call it.
`py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py::ready` also calls
it, but only the Dev Container runs that phase.
