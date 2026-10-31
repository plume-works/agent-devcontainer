---
type: architecture
description: A Remote Control server revives every earlier session in its own current spawn mode, so after a worktree-to-same-dir switch the former worktree sessions run in the workspace folder; the maintainer accepts this because spawn mode is not switched in production.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T04:32:14Z
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/remote_control.py
---

# Claude Remote Control spawn mode switch

Finding against [Claude Remote Control server
mode](claude-remote-control-server-mode.md) and [Claude Remote Control worktree
restart resume](claude-remote-control-worktree-restart-resume.md), measured on
Claude Code 2.1.310 by restarting the server with `AGENTDEV_CLAUDE_RC_SPAWN`
switched between `worktree` and `same-dir`.

## Measurement

- **Every session returns whatever the spawn mode.** Each restart brought back
  all earlier sessions, both those spawned in `same-dir` mode and those spawned
  in `worktree` mode.
- **A revived session takes the reviving server's spawn mode.** Under a
  `same-dir` server, sessions first spawned in their own worktrees run in the
  workspace folder, on the branch checked out there. Their worktrees and
  `worktree-bridge-<session ID>` branches stay on disk, unused.
- **Re-entering the worktree holds only for an unchanged spawn mode.** The
  worktree return the earlier finding records is what a `worktree` server does.

## Decision

The maintainer decided not to work around this: the spawn mode is not switched
in production, so a session never meets a server of another spawn mode there.

## Consequences

- After switching the spawn mode, a former worktree session edits and commits in
  the workspace folder, next to every other session working there.

## Closing

Closed: accepted as a limit of switching the spawn mode.
