---
type: architecture
description: After a devcontainer rebuild or a server restart, sessions that `claude remote-control --spawn worktree` spawned on demand return in their own worktrees with their earlier turns and no user action, after a delay from seconds to several minutes.
generated:
  by: claude-code/opus-5
  at: 2026-10-26T02:55:00Z
sources:
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: https://github.com/anthropics/claude-code/issues/104940
---

# Claude Remote Control worktree restart resume

Finding against [Claude Remote Control server
mode](claude-remote-control-server-mode.md) and [Claude Remote Control server
restart resume](claude-remote-control-server-restart-resume.md), measured on
Claude Code 2.1.310 with `claude remote-control --spawn worktree` across a
devcontainer rebuild and a later server restart.

## Measurement

- **Spawned worktree sessions return.** Each one comes back under the same
  session ID with its earlier turns. The new process's working directory is that
  session's own `.claude/worktrees/bridge-<session ID>` worktree, which the
  rebuild leaves in place, still registered and locked in git, on its
  `worktree-bridge-<session ID>` branch.
- **Waiting is the only recovery.** Neither the Claude app nor claude.ai/code
  lets a user send to an offline session, so every return happened with no user
  action.
- **The return is delayed and uneven.** The pre-created session returns within
  seconds of the server starting. After the rebuild, three spawned sessions
  returned 3 min 19 s to 3 min 46 s after the server started and the fourth 8
  min 45 s after. After the later server restart, two returned within 5 s and
  the other two after 43 s.
- **No `initialize` pair shows in a worktree session's transcript.** Unlike the
  `same-dir` dispatch, the worktree transcripts record no `initialize` control
  requests around the return.

## Relation to the upstream report

[anthropics/claude-code#104940](https://github.com/anthropics/claude-code/issues/104940)
reports on 2.1.284 that worktree sessions stay offline after a server restart
until a message is sent. Here no message could be sent and every session
returned, so the report may describe sessions that were still inside this delay.

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
