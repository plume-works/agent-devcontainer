---
type: architecture
description: After a Remote Control server restart, a same-dir session spawned on demand is not reattached at server start; a get_session lookup of that session prompts the server to spawn it again under the same ID within seconds.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-24T02:06:00Z
sources:
- resource: .devcontainer/scripts/claude-remote-control-start.sh
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
  pre-created session or one started from the Claude app, is not reattached at
  server start. claude.ai lists it as disconnected with a recoverable
  `computer_unreachable` init error stamped at server start, and the server does
  not count it toward its capacity.
- **A `get_session` lookup of a disconnected session wakes it.** The server
  spawns it again, under the same ID with its earlier turns, five to fifteen
  seconds after the lookup, with no message sent to it. A disconnected session
  can therefore be recovered on demand from any session that holds the
  `claude-code-remote` tools.

The server's process tree right after a restart, with its spawned sessions still
disconnected:

``` text
tmux -L claude-remote
└─ claude remote-control --spawn same-dir --name agent-dev1
   └─ claude --print --session-id <pre-created> --resume=…
```

The same tree after a `get_session` lookup of each spawned session:

``` text
tmux -L claude-remote
└─ claude remote-control --spawn same-dir --name agent-dev1
   ├─ claude --print --session-id <pre-created> --resume=…
   ├─ claude --print --session-id <fork> --resume=…
   └─ claude --print --session-id <app-started> --resume=…   (one per woken session)
```

## Hypotheses eliminated

- **The spawned session is lost.** Eliminated: it returns with its history.
- **The server reattaches it after a fixed delay.** Eliminated: without a
  claude.ai-side request, no spawned session returned within seven minutes of a
  restart.
- **A message to the session wakes it.** Eliminated: messages sent to it from
  the Claude app while it was disconnected left it disconnected, and its
  transcript shows the resume `SessionStart` with no incoming message before it.
- **Opening the session in the Claude app wakes it.** Eliminated: it stayed
  disconnected while open in the app to send those messages.
- **Local inspection of server state wakes it.** Eliminated: process listings,
  `bridge-spawn` and pane reads alone left it disconnected.
- **A `list_sessions` call wakes it.** Eliminated: a single `list_sessions` call
  from the pre-created session left every spawned session disconnected for more
  than five minutes.

## Open questions

- **Whether one lookup always wakes a session.** Of three `get_session` lookups
  issued in parallel, two woke their sessions and one did not; a later single
  lookup of that session woke it. Settling it takes a restart, then one lookup
  per disconnected session, issued sequentially with a gap, and a count of the
  sessions that return.
- **Whether the respawn is bound by the documented four-hour resume window.**
  Settling it takes a `get_session` lookup more than four hours after a restart.

## Closing

The finding closes when both questions are measured, or when the maintainer
decides the measurement is not worth the cost because server mode remains an
opt-in trial.
