---
type: task
description: Replace the Coder agent's one-shot Remote Control start with a supervised service, like the standalone runtime's remote-control watcher, so a Coder workspace starts Remote Control after a later claude.ai login and restarts a session that exits.
stage: planned
priority: medium
created: 2026-10-28
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T04:39:39Z
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/coder.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/remote_control.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/supervisor.py
- resource: docs/knowledge/data/plans/20261027-standalone-remote-control-autostart.md
---

# Supervise Claude Remote Control in Coder workspaces

The Coder template's `coder_script` runs `agentdev-runtime coder start` on every
agent start, which ends by running `agentdev-runtime remote-control start` once
(`agentdev_runtime/coder.py`). With no claude.ai login at that moment, Remote
Control stays off until the operator runs the script by hand or restarts the
agent, and nothing restarts a `claude-remote` session that exits. The standalone
runtime already solves both with its supervised `remote-control` watcher ([Start
Claude Remote Control in the standalone
runtime](../plans/20261027-standalone-remote-control-autostart.md)). The
maintainer wants the same service in Coder workspaces; other Dev Containers
starts (VS Code, the devcontainer CLI) stay without Remote Control autostart.

## What to do

- Run the Remote Control start in Coder under supervision instead of as a
  one-shot: wait for a claude.ai login without polling `claude auth status` on
  every tick, start `claude-remote` once the login exists, and restart a session
  it saw live that is gone, within a bounded recovery budget.
- Reuse `agentdev-runtime remote-control` where it fits, and keep the existing
  behavior that `spec/claude-remote-control` requires of Coder starts: the Coder
  user secrets and git credential helper reach the Claude process,
  `CODER_WORKSPACE_NAME` names the session, and a live session is reused.
- Decide how Coder reports the service's state, since Coder workspaces have no
  `agentdev-runtime health status`.

## Why it matters

A workspace started before the operator's first `/login`, or whose Remote
Control server exits after an extended outage, has no Remote Control until
someone notices and intervenes.
