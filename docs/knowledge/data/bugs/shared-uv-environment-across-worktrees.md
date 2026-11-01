---
type: bug
description: Every checkout in one devcontainer shares the uv environment at /uv/venvs/ws-project, so a uv run in one worktree repoints the editable agentdev_runtime and validate_agent_files installs and dependencies, and other worktrees' tests run its code.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T03:00:00Z
sources:
- resource: .devcontainer/devcontainer.json
- resource: py_packages/agentdev_runtime/agentdev_runtime/project.py
---

# Bug: worktrees in one devcontainer share the uv environment

## Symptom

Tests that pass alone fail inside a longer run when another agent session works
in a different worktree of the same devcontainer. Subprocesses import
`agentdev_runtime` from the other worktree, for example
`ImportError: cannot import name 'codex_config' from 'agentdev_runtime' (.../.claude/worktrees/<other>/py_packages/agentdev_runtime/...)`,
or the `doctor` tests in `test_environment_health.py` see another revision's
output. A failed run is then repeated in full, which made a Ship gate rerun take
a 14-minute suite twice.

## Reproduction

In one devcontainer, start `uv run pytest scripts/tests` in worktree A. While it
runs, start any `uv run` in worktree B, which has a different
`agentdev_runtime`. `uv run` in B reports
`Uninstalled 2 packages … Installed 2 packages`, and A's remaining
`python -m agentdev_runtime` subprocesses run B's code.

## Root cause

`devcontainer.json` sets `UV_PROJECT_ENVIRONMENT` to one fixed path on the `/uv`
volume, on the premise that each devcontainer serves one checkout. Git worktrees
inside the container are several checkouts on that one volume. The project's
packages are editable installs, and every `uv run` syncs them to point at the
invoking checkout, so the last checkout to run owns the environment.

## Fix

Not fixed. Each checkout needs its own environment: a `.venv` link into a
per-checkout directory on the `/uv` volume keeps it hardlinked to the cache
there.

## Key references

Verified anchor points (line numbers as of 2026-10-31):

- `.devcontainer/devcontainer.json:49` — the fixed `UV_PROJECT_ENVIRONMENT`
- `.devcontainer/devcontainer.json:172` — `python.defaultInterpreterPath`
- `py_packages/agentdev_runtime/agentdev_runtime/project.py:23` —
  `MANAGED_VENV_PREFIX`
- `py_packages/agentdev_runtime/agentdev_runtime/project.py:31` — `sync`, which
  removes a `.venv` link into `/uv/venvs/`
