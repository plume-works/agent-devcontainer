---
type: architecture
description: A Remote Control server started without bridge-pointer.json pre-creates a fresh session in the workspace folder, unless a terminal Remote Control session already runs in that folder, in which case it exits at once; with a pointer present it starts regardless.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-27T17:20:00Z
sources:
- resource: .devcontainer/scripts/claude-remote-control-start.sh
---

# Claude Remote Control pointerless server start

Finding against [Claude Remote Control archived pre-created
session](claude-remote-control-archived-pre-created-session.md), measured on
Claude Code 2.1.310 with `claude remote-control --spawn worktree` and
`--create-session-in-dir` at its default, on.

## Measurement

- **No pointer, folder free: a fresh session is pre-created.** With
  `~/.claude/projects/<workspace>/bridge-pointer.json` removed, the server
  registers a new bridge environment, pre-creates a new session in the workspace
  folder, and writes a pointer naming it.
- **No pointer, folder taken: the server exits.** When a terminal Remote Control
  session already runs in the workspace folder, the server prints
  ``Error: This folder is already served by a terminal `claude remote-control` on this device. Stop it first.``
  and exits 1 within five seconds. Under the start script the tmux pane exits
  with it, and nothing restarts the server.
- **What takes the folder.** A live `~/.claude/sessions/<pid>.json` entry whose
  `cwd` is the workspace folder and which carries a `bridgeSessionId`, such as a
  `claude --resume <id> --remote-control` session started there.
- **A pointer bypasses the check.** With a pointer present, the server starts
  and re-adopts the pointer's session while the same terminal session runs in
  the folder.

## Hypotheses eliminated

- **A race with the server just stopped.** Eliminated: the pointerless start
  still failed after ten seconds with no server process left, and succeeded
  under the same conditions once a pointer was restored.

## Open questions

- **Whether a stopped server's own pre-created session blocks a pointerless
  restart.** Its child is a terminal-registered session in the workspace folder
  until it exits. Settling it takes stopping the server, removing the pointer,
  and starting again at once with no other session in the folder, with
  `--debug-file` on.

## Closing

Clearing an archived pointer brings back a pre-created session only when no
terminal Remote Control session runs in the workspace folder. Closes with the
decision on the archived-pointer fix: a start script that clears the pointer
must either confirm the folder is free or accept a server that exits at start.
