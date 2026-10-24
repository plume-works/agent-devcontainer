---
type: architecture
description: After a Remote Control server restart, a same-dir session spawned on demand is not reattached at server start; it stays disconnected until something on the claude.ai side prompts the server to spawn it again under the same ID.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-24T01:55:00Z
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
  `computer_unreachable` init error, and the server does not count it toward its
  capacity. The server later spawns it again, under the same ID with its earlier
  turns, without any message being sent to it. Each observed respawn followed,
  by twenty seconds to two minutes, a `list_sessions` call made from the
  pre-created session.

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

## Open questions

- **Whether a session listing triggers the respawn.** A `list_sessions` call is
  the only remaining candidate. Settling it takes a restart, a wait past the
  observed two-minute lag with no listing, then a single `list_sessions` call.
- **Whether the respawn is bound by the documented four-hour resume window.**
  Settling it takes the same trigger more than four hours after a restart.

## Closing

The finding closes when both questions are measured, or when the maintainer
decides the measurement is not worth the cost because server mode remains an
opt-in trial.
