---
type: architecture
description: After a devcontainer rebuild, sessions that `claude remote-control --spawn worktree` spawned on demand return in their own worktrees with their earlier turns and no user action, some several minutes after the server starts.
generated:
  by: claude-code/opus-5
  at: 2026-10-26T02:50:00Z
sources:
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: https://github.com/anthropics/claude-code/issues/104940
---

# Claude Remote Control worktree restart resume

Finding against [Claude Remote Control server
mode](claude-remote-control-server-mode.md) and [Claude Remote Control server
restart resume](claude-remote-control-server-restart-resume.md), measured on
Claude Code 2.1.310 with `claude remote-control --spawn worktree` across a
devcontainer rebuild.

## Measurement

- **Spawned worktree sessions return.** Each one comes back under the same
  session ID with its earlier turns. The new process's working directory is that
  session's own `.claude/worktrees/bridge-<session ID>` worktree, which the
  rebuild leaves in place, still registered and locked in git, on its
  `worktree-bridge-<session ID>` branch.
- **They return without any user action.** While a session is offline, the
  Claude app offers no way to send it a message, so nothing in the app can wake
  it.
- **The return is late and uneven.** The pre-created session returned within
  seconds of the server starting. Three spawned sessions returned between 3 min
  19 s and 3 min 46 s after the server started; the fourth returned 8 min 45 s
  after.
- **No `initialize` pair shows in a worktree session's transcript.** Unlike the
  `same-dir` dispatch, the worktree transcripts record no `initialize` control
  requests around the return.

## Relation to the upstream report

[anthropics/claude-code#104940](https://github.com/anthropics/claude-code/issues/104940)
reports on 2.1.284 that worktree sessions stay offline after a server restart
until a message is sent. Here every session returned with no message sent, so
the report may describe sessions that were still inside this delay.

## Open questions

- **What sets the delay and its upper bound.** Settling it needs more restarts
  with timed returns, or the service's dispatch rules.
- **What carries the dispatch for a worktree session**, given that its
  transcript holds no `initialize` pair.

## Closing

Worktree sessions do return to their worktrees after a restart, so the delay
does not block the worktree default. The finding closes when the open questions
are measured, or when the maintainer decides the measurement is not worth the
cost.
