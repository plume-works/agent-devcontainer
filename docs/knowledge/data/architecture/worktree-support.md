---
type: architecture
description: Git worktrees work in the Dev Container, but it gives them nothing of their own — every worktree shares the checkout's uv environment and agentdev catalog.
sources:
- resource: .devcontainer/devcontainer.json
- resource: py_packages/agentdev_runtime/agentdev_runtime/remote_control.py
---

# Worktree support

## Decision

The maintainer decided that the Dev Container gives git worktrees nothing of
their own. A worktree works as git makes it, but every worktree in one Dev
Container shares the checkout's environment:

- the uv environment at `UV_PROJECT_ENVIRONMENT` (`/uv/venvs/ws-project`), so a
  `uv run` in one worktree repoints the editable installs and dependencies every
  other worktree uses ([uv environment location](uv-environment-location.md));
- the agentdev catalog registered at the main checkout, so a session in a
  worktree runs the main checkout's skills and agents.

Remote Control server mode spawns conversations in the workspace folder by
default ([Claude Remote Control server
mode](claude-remote-control-server-mode.md)), so nothing in the Dev Container
creates worktrees unless a person or a session asks for one.

## What the decision leaves in place

- `git-new-branch --worktree` still creates a branch in a new worktree.
- `AGENTDEV_CLAUDE_RC_SPAWN=worktree` still gives each spawned Remote Control
  conversation its own worktree under `.claude/worktrees/`.
- [Worktree hooks](worktree-hooks.md) still describes how a `WorktreeCreate` or
  `WorktreeRemove` hook is written; none is registered.

## Rejected alternatives

- **One uv environment per checkout**, a `.venv` link into
  `/uv/venvs/<checkout name>` that git's `post-checkout` hook, a
  `WorktreeCreate` hook, and the attach phase create
  ([plan](../plans/20261101-per-checkout-uv-environments.md), cancelled). Every
  way a worktree is created needs its own trigger, and the `post-checkout` hook
  lands in the `.git/hooks` a macOS host shares through the bind mount, where it
  fails every host checkout without pre-commit.
- **One agentdev catalog per Claude worktree**, read live from the worktree
  through `WorktreeCreate` and `WorktreeRemove` hooks
  ([plan](../plans/20261103-per-worktree-catalog.md), cancelled).

## Consequences

- Concurrent sessions in different worktrees of one Dev Container can run each
  other's code; [the shared uv environment
  bug](../bugs/shared-uv-environment-across-worktrees.md) is closed as won't
  fix.
