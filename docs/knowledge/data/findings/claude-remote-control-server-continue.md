---
type: finding
description: claude remote-control --continue cannot be combined with server-mode flags and runs a single session, so server mode keeps starting without it.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/remote_control.py
---

# Claude Remote Control server --continue

Finding against [Claude Remote Control server restart
resume](claude-remote-control-server-restart-resume.md), on Claude Code 2.1.309.

## Question

Whether starting the server with `--continue` changes which sessions return
after a server restart.

## Measurement

- **`--continue` is refused alongside server-mode flags.**
  `claude remote-control --spawn same-dir --continue` exits with
  `--session-id and --continue cannot be used with --spawn, --capacity, or --create-session-in-dir.`
  In the start script that error ends the tmux pane, and Remote Control does not
  start.
- **On its own, `--continue` runs a single session.**
  `claude remote-control --continue` reattaches the session last recorded for
  the directory, here the server's pre-created session, and reports
  `Single session · exits when complete`. It spawns no other sessions and does
  not reattach the ones the server had spawned.
- **Spawned sessions stay disconnected under `--continue`.** A single-session
  process cannot spawn, so the dispatches the service sends for them go
  unanswered until server mode runs.

## Closing

Closed: `--continue` is incompatible with server mode.
