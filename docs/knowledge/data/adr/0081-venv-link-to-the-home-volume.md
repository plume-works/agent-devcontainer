---
type: adr
stage: accepted
description: Each checkout links its .venv to its own uv environment in the venv root on the home volume.
---

# Each checkout links .venv to its own environment on the home volume

The uv environments are in the venv root on the home volume, next to the uv
cache. As a result, uv can hardlink packages from the cache. Each checkout gets
its own environment, because `uv run` points editable installations at the
checkout that calls it. A `.venv` link in the checkout selects the environment,
so each `uv run` finds it with no wrapper
(`py_packages/agentdev_runtime/agentdev_runtime/project.py::link_venv`).

## Considered Options

- A `.venv` directory in the checkout. Rejected: it is on the workspace bind
  mount, where uv copies files with no message and does not hardlink them. On a
  macOS host, each uv file operation then goes through VirtioFS.
- `UV_PROJECT_ENVIRONMENT`. Rejected: it has one value for the whole container,
  and uv ignores `.venv` while it is set. A value for each checkout from a `uv`
  wrapper or `CLAUDE_ENV_FILE` applies to one session only.
- One shared environment without editable installations. Rejected: the
  dependencies of branches are still different.
- `UV_LINK_MODE=symlink`. Rejected: when uv cleans its cache, each environment
  breaks.
- A `PreToolUse`, `SessionStart`, or `SubagentStart` hook. Rejected:
  `PreToolUse` runs at each tool call, `SessionStart` at each session, and
  `SubagentStart` at a dispatch, not when Claude Code makes a worktree. A
  session that disables the plugin gets no plugin hook.

## Consequences

- The attach phase and the `WorktreeCreate` hook make the link for one checkout
  only. The attach phase then removes each environment in the venv root that no
  checkout uses
  (`py_packages/agentdev_runtime/agentdev_runtime/project.py::prune_venvs`).
- The mounted checkout belongs to the container. A host that works in it sets
  its own `UV_PROJECT_ENVIRONMENT`.
