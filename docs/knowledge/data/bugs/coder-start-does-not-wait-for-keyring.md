---
type: bug
description: agentdev-runtime coder start runs the git credential helper setup at once, so when gh keeps its login in the keyring and the keyring session is not ready, HTTPS git gets no gh login.
stage: pending
severity: medium
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/coder.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/git.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: docs/knowledge/data/findings/spec-usefulness-audit.md
- resource: docs/spec-audit/requirements.jsonl
---

# Bug: the Coder start sets up the git credential helper without a wait for the keyring

## Symptom

HTTPS git must use the gh login, and the check of that login must occur only
after the keyring session is available. The Dev Container start phase waits for
the runtime. `agentdev-runtime coder start` does not wait. When it runs before
the keyring session file exists, the helper setup cannot read the login, writes
a warning, and Remote Control starts without a working helper.

## Reproduction

1. In a Coder workspace where gh keeps its login in the keyring, let the Coder
   agent start before the runtime writes the keyring session file.
2. The agent log shows "Warning: git credential helper setup failed; starting
   Remote Control anyway.".
3. A later `git fetch` over HTTPS cannot authenticate.

## Root cause

`py_packages/agentdev_runtime/agentdev_runtime/coder.py::start` runs
`agentdev-runtime git credential-helper` with no wait.
`py_packages/agentdev_runtime/agentdev_runtime/git.py::keyring_environment`
reads the keyring session file only if it exists.
`py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py::ready` waits for
the runtime first, but the Coder start does not use it. The order now depends on
when Coder starts the agent, not on this repository.
