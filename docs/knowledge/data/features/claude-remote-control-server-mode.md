---
type: feature
stage: implemented
description: Setting AGENTDEV_CLAUDE_RC_MODE=server makes the autostarted claude-remote session run Claude Remote Control in server mode, so new conversations can be spawned in the workspace from claude.ai/code, the Claude mobile app, or a claude.ai Project.
generated:
  by: claude-code/opus-5
  at: 2026-10-25T19:10:00Z
sources:
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: https://code.claude.com/docs/en/remote-control
- resource: https://code.claude.com/docs/en/claude-projects
- resource: https://code.claude.com/docs/en/worktrees
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
`claude-remote-control-start.sh` run `claude remote-control` in the
`claude-remote` tmux session. Unset, or `session`, keeps the pinned interactive
pane.

**A worktree per conversation by default.** Each conversation spawned on demand
works in its own git worktree under the workspace folder's `.claude/worktrees/`,
so concurrent conversations do not edit the same files.
`AGENTDEV_CLAUDE_RC_SPAWN=same-dir` makes every spawned conversation work in the
workspace folder instead. The conversation the server pre-creates works in the
workspace folder either way.

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
- **An unrecognized spawn value.** In server mode the script prints the valid
  options and fails without starting a session; in session mode the value is
  ignored.

## Open questions

- Do concurrent spawned conversations race the single-use OAuth refresh token?
  Each runs as its own `claude` process with access to the credential store.
- Do the worktrees of finished spawned conversations accumulate? Spawned
  sessions run as `claude --print` ([restart resume
  finding](../architecture/claude-remote-control-server-restart-resume.md)), and
  Claude Code documents no worktree cleanup for `-p` runs.
