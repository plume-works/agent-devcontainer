---
type: architecture
description: After a Remote Control server restart, a same-dir session spawned on demand returns when the claude.ai service dispatches it to the server as a pair of initialize control requests; the service skips some sessions at server start and dispatches them later on its own.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T04:32:14Z
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/remote_control.py
---

# Claude Remote Control server restart resume

Finding against [Claude Remote Control server
mode](claude-remote-control-server-mode.md), measured on Claude Code 2.1.309
with `claude remote-control --spawn same-dir`.

## Measurement

After the server restarts, its sessions return in two different ways:

- **The pre-created session** is reattached at server start, under the same ID
  with its earlier turns.
- **A session spawned on demand** in the same directory, whether a fork of the
  pre-created session or one started from the Claude app, returns only when the
  claude.ai service dispatches it. Until then claude.ai lists it as disconnected
  with a recoverable `computer_unreachable` init error, and the server does not
  count it toward its capacity.
- **A dispatch is a pair of `initialize` control requests** written to the
  session's transcript. While the server runs, it spawns the session again in
  the same second, under the same ID with its earlier turns, and the new process
  answers the pair. A pair written while no server runs stays unanswered.
- **The service dispatches at server start, but not every session.** Most
  disconnected sessions get a pair within seconds of the server connecting. At
  each start the service can skip a session, a different one from one start to
  the next, and the same session can be skipped at several starts in a row.
- **A skipped session is dispatched later without any action.** A session the
  service skipped got its pair about ninety seconds after the server started,
  with no restart, lookup or message in between.
- **A spawned session can start twice for one wake.** The server once started a
  second process for the same session within fifteen seconds of the first.

The server's process tree right after a restart, with its spawned sessions still
disconnected:

``` text
tmux -L claude-remote
└─ claude remote-control --spawn same-dir --name agent-dev1
   └─ claude --print --session-id <pre-created> --resume=…
```

The same tree once each spawned session has been dispatched:

``` text
tmux -L claude-remote
└─ claude remote-control --spawn same-dir --name agent-dev1
   ├─ claude --print --session-id <pre-created> --resume=…
   ├─ claude --print --session-id <fork> --resume=…
   └─ claude --print --session-id <app-started> --resume=…   (one per dispatched session)
```

## Hypotheses eliminated

- **The spawned session is lost.** Eliminated: it returns with its history.
- **The server ignores a dispatch.** Eliminated: every pair that arrived while
  the server ran was followed by a spawn in the same second; every miss was a
  missing pair.
- **The session's own state makes it unwakeable.** Eliminated: the skipped
  session changed between restarts, and every skipped session was dispatched
  later.
- **A message to the session wakes it.** Eliminated: messages sent to it from
  the Claude app while it was disconnected left it disconnected, and its
  transcript shows the resume `SessionStart` with no incoming message before it.
- **Opening the session in the Claude app wakes it.** Eliminated: it stayed
  disconnected while open in the app to send those messages.
- **Local inspection of server state wakes it.** Eliminated: process listings,
  `bridge-spawn` and pane reads alone left it disconnected.
- **A claude.ai lookup wakes it.** Eliminated as a reliable trigger: a single
  `list_sessions` call, and a burst of five `get_session` lookups, each left the
  session disconnected with no pair written. Respawns that followed a lookup
  also followed a pair within seconds, which accounts for them.

## Open questions

- **What makes the service skip a session at server start, and what schedules
  its later dispatch.** The pairs are written on the claude.ai side, so the
  server cannot be changed to avoid the skip. Settling it needs either the
  service's dispatch rules or enough restarts to correlate skips with session
  attributes.
- **Whether dispatch is bound by the documented four-hour resume window.**
  Settling it takes a disconnected session observed past four hours after a
  restart.

## Closing

The skip recovers on its own within minutes, so it does not block server mode.
The finding closes when the open questions are measured, or when the maintainer
decides the measurement is not worth the cost because server mode remains an
opt-in trial.
