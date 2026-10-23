---
type: feature
stage: accepted
description: Setting AGENTDEV_CLAUDE_RC_MODE=server makes the autostarted claude-remote session run Claude Remote Control in server mode, so new conversations can be spawned in the workspace from claude.ai/code, the Claude mobile app, or a claude.ai Project.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-24T00:10:00Z
sources:
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: https://code.claude.com/docs/en/remote-control
- resource: https://code.claude.com/docs/en/claude-projects
---

# Remote Control server mode

## Purpose

The autostarted Remote Control pane serves one pinned conversation. Starting a
fresh conversation from a phone or browser needs a terminal and `/clear`, and a
claude.ai Project cannot run a thread in the workspace. Server mode lets the
workspace accept new conversations from any connected device.

## Behaviour

**Opt-in by environment.** `AGENTDEV_CLAUDE_RC_MODE=server` — for example a
Coder env user secret, which the `coder_script` inherits — makes
`claude-remote-control-start.sh` run `claude remote-control --spawn same-dir` in
the `claude-remote` tmux session. Unset, or `session`, keeps the pinned
interactive pane.

**Same directory.** Every spawned conversation works in the workspace folder.

**Same environment.** Spawned conversations inherit the Coder agent's
environment, Coder user secrets and git credentials included.

The contract is [Claude Remote Control](../spec/claude-remote-control.md).

## Edge cases

- **An unrecognized mode value.** The script prints the valid options and fails
  without starting a session.
- **A session is already running.** It is reused, so a mode change applies on
  the next session start.
- **The server has been stopped for more than about four hours.** Its sessions
  are not brought back; the next start begins new ones.
- **The workspace is offline for more than about ten minutes.** The server
  exits, and Remote Control stays off until the next agent start.
- **Worktree spawn mode.** Not offered: a spawned worktree session did not
  survive a server restart.

## Open questions

- Do concurrent spawned conversations race the single-use OAuth refresh token?
  Each runs as its own `claude` process with access to the credential store.
