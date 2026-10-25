---
type: task
description: When AGENTDEV_CLAUDE_RC_MODE is set, the standalone agent-opencode runtime runs claude-remote-control-start.sh as an optional component; unset, Remote Control stays off as it is today.
stage: planned
priority: high
created: 2026-10-25
generated:
  by: claude-code/opus-5.5
  at: 2026-10-25T03:23:30Z
sources:
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: .devcontainer/scripts/coder-agent-start.sh
- resource: .devcontainer/scripts/runtime-supervisor.py
- resource: docker/opencode/supervisord.conf
- resource: compose.opencode.yml
---

# Start Claude Remote Control in the standalone runtime when asked

Only the Coder agent starts Claude Remote Control today
(`coder-agent-start.sh:21`). The standalone `agent-opencode` runtime has no
component for it, so a project container never starts it, even after a claude.ai
login. The [standalone OpenCode container
plan](../plans/20261017-standalone-opencode-container.md) left Remote Control
autostart out of scope, and [Claude Remote
Control](../spec/claude-remote-control.md) scopes autostart to the Coder agent.
The maintainer has asked for standalone support, gated on
`AGENTDEV_CLAUDE_RC_MODE`.

## What to do

- **Gate.** A nonempty `AGENTDEV_CLAUDE_RC_MODE` (`session` or `server`) turns
  the component on, and unset or empty leaves it off. The gate belongs in the
  runtime, not the start script: the script treats an unset mode as `session`
  (`claude-remote-control-start.sh:4`). An unrecognized value latches a
  configuration failure, as the other settings do.
- **Component.** Add an optional `remote-control` one-shot to `SERVICES` and
  `supervisord.conf` that runs `claude-remote-control-start.sh` as the runtime
  user, after `prepare`. The script starts a detached `tmux -L claude-remote`
  session and exits, so it fits a one-shot. Its failure degrades the runtime and
  never latches it outside strict startup.
- **Login after start.** The script exits `0` and skips when there is no
  claude.ai login, which is the usual state on a project's first start. Decide
  how a later login starts Remote Control:
  `runtime-supervisor.py retry remote-control`, the next container start, or a
  supervised watcher. Record the choice, because "skipped, no login" must not
  report as `done`.
- **Settings.** `compose.opencode.yml` passes `AGENTDEV_CLAUDE_RC_MODE` through,
  and `runtime.env.example` documents it.
- **Docs and spec.** Extend [Claude Remote
  Control](../spec/claude-remote-control.md) to the standalone runtime, and
  update the standalone runtime architecture doc and README.

## Done when

- With the mode unset, no `claude-remote` tmux session exists and the runtime
  reports no `remote-control` component.
- With `server` or `session` and a claude.ai login, the runtime starts
  `claude-remote` in the workspace folder with no terminal interaction. A
  conversation started from claude.ai/code works there.
- With the mode set and no login, the runtime stays `ready`, `status` says
  Remote Control is waiting for a login, and the chosen trigger starts it once
  the login exists.
- Supervision tests cover the gate and the skip, and native acceptance covers
  the started session, using a fake `claude` because acceptance has no claude.ai
  login.
