---
type: architecture
description: Once the session a Remote Control server pre-created in the workspace folder is archived on claude.ai, every later server start re-adopts that archived session, which ends within a second, and no replacement is pre-created, so the folder runs with no session until a new one is started on demand.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-26T18:50:00Z
sources:
- resource: .devcontainer/scripts/claude-remote-control-start.sh
---

# Claude Remote Control archived pre-created session

Finding against [Claude Remote Control server
mode](claude-remote-control-server-mode.md) and [Claude Remote Control server
restart resume](claude-remote-control-server-restart-resume.md), measured on
Claude Code 2.1.310 with `claude remote-control --spawn worktree` and
`--create-session-in-dir` at its default, on.

## Measurement

- **An archived pre-created session does not come back, and is not replaced.**
  The server keeps the pre-created session's ID in
  `~/.claude/projects/<workspace>/bridge-pointer.json`. At start it re-adopts
  that ID whether or not the session is archived, and pre-creates no new session
  in its place. The pointer keeps naming the archived session, rewritten hourly
  while the server runs, so every later start repeats this.
- **The re-adopted session ends within a second.** `bridge/reconnect` first
  answers `Session not found` for the `session_` ID, then succeeds for the
  `cse_` ID and re-queues it. The server spawns it in the workspace folder; the
  service sends the child `end_session` with reason `archived`, the child logs
  `CCRClient: Epoch mismatch (409, reason=session_not_active)` and exits 1, and
  the pane reports `Session failed: Process exited with error`. The server then
  returns to `Ready` at zero capacity used.
- **Archived spawned sessions fail the same way, and leave a worktree.** In
  `worktree` mode the server creates a fresh `.claude/worktrees/bridge-<ID>`
  worktree and `worktree-bridge-<ID>` branch for an archived spawned session
  before it ends, and keeps them, locked, after the session fails.
- **Live spawned sessions are unaffected.** An unarchived spawned session
  returned in its own worktree with its earlier turns, within the delay [Claude
  Remote Control worktree restart
  resume](claude-remote-control-worktree-restart-resume.md) records.

## Hypotheses eliminated

- **Worktree spawn mode breaks the resume.** Eliminated: the pre-created session
  fails in the workspace folder with no worktree, and the child's debug log
  shows the service ending it as archived before any local resume step fails.

## Open questions

- **Whether the service stops dispatching archived sessions.** Settling it takes
  restarts spread past the four-hour resume window, watching whether the
  archived IDs are still re-queued.
- **Whether `--create-session-in-dir` pre-creates a session once the pointer is
  gone.** Settling it takes one server start with `bridge-pointer.json` removed.

## Closing

Closes when the maintainer decides whether the start script should detect an
archived pointer session and clear the pointer so the server pre-creates a new
one, or accepts running without a pre-created session after an archive.
