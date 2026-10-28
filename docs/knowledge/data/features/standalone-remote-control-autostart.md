---
type: feature
stage: accepted
description: In the standalone agent-opencode runtime, setting AGENTDEV_CLAUDE_RC_MODE to session or server runs a supervised watcher that starts Claude Remote Control once a claude.ai login exists, keeps the session alive, and reports that it is waiting while no login exists; unset leaves Remote Control off.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-27T12:00:00Z
sources:
- resource: docs/knowledge/data/backlog/standalone-claude-remote-control.md
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: .devcontainer/scripts/runtime-supervisor.py
- resource: .devcontainer/scripts/runtime-health.sh
- resource: docker/opencode/supervisord.conf
- resource: compose.opencode.yml
---

# Remote Control autostart in the standalone runtime

## Purpose

Only the Coder agent starts Claude Remote Control. A standalone `agent-opencode`
project container never does, even with a claude.ai login in its auth volume, so
reaching it from claude.ai/code or the Claude mobile app needs a manual start
inside the container after every restart.

## Behaviour

**Opt-in by mode.** `AGENTDEV_CLAUDE_RC_MODE=session` or `server` adds a
`remote-control` component to the runtime; unset or empty leaves it out
entirely. The mode means what it means on Coder: `session` resumes one pinned
conversation, `server` spawns conversations on demand.

**Starts once a login exists.** The component is a supervised watcher. While no
claude.ai login exists it waits, and `runtime-health.sh status` says it is
waiting for a claude.ai login; the runtime stays `ready`. Once `/login`
completes in any container sharing the auth volume, the watcher starts
`claude-remote` in the workspace folder with no further operator action.

**Stays up.** When a running `claude-remote` session disappears, the watcher
restarts it within the runtime's recovery budget. A budget it exhausts degrades
the runtime, as any optional component does, unless strict startup is selected.

## Edge cases

- **The mode is misspelled.** The runtime latches a configuration failure naming
  the variable, before startup, as with its other settings.
- **The login expires.** The watcher returns to waiting rather than failing.
- **The watcher itself restarts.** It adopts a live `claude-remote` session
  instead of starting a second one.

## Open questions

None — the design is settled.

## References

- Plan: [Start Claude Remote Control in the standalone
  runtime](../plans/20261027-standalone-remote-control-autostart.md)
- Task: [Start Claude Remote Control in the standalone runtime when
  asked](../backlog/standalone-claude-remote-control.md)
- Coder counterpart: [Remote Control autostart on
  Coder](coder-remote-control-autostart.md)
