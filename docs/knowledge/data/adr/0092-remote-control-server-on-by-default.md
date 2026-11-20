---
type: adr
stage: accepted
description: The `claude remote-control` server is the only Remote Control mode, it runs by default, and AGENTDEV_CLAUDE_RC_SPAWN selects its spawn mode or `off`.
supersedes:
- adr/0077-remote-control-server-mode-is-opt-in
- adr/0078-remote-control-starts-from-the-agent-start
- adr/0080-session-mode-pins-one-conversation
---

# The Remote Control server runs by default

The `claude remote-control` server is the only Remote Control mode, and it runs
by default. `AGENTDEV_CLAUDE_RC_SPAWN` selects the spawn mode: `worktree` (the
default, by decision of the maintainer), `same-dir`, or `session`. The value
`off` stops Remote Control. A value that is not in this list stops the start, so
that an incorrect value does not run a different mode with no message.

## Considered Options

- Keep the tmux pane that holds one conversation as a second mode. Rejected:
  `--spawn session` gives the server one conversation, so a second mode adds
  code and gives no new function.
- Keep `AGENTDEV_CLAUDE_RC_MODE` with the values `server` and `off`. Rejected:
  with one mode, a second variable holds only the off value.
- A boolean variable for Remote Control. Rejected: it is a second variable next
  to the spawn mode, which can hold the off value.

## Consequences

- No Dev Container lifecycle command starts Remote Control. In a Coder
  workspace, the Coder agent start `agentdev-runtime coder start` starts it. A
  runtime supervisor starts it with its `remote-control` watcher. Both skip the
  start when the spawn mode is `off`.
- `AGENTDEV_CLAUDE_RC_MODE` has no effect. A runtime that set
  `AGENTDEV_CLAUDE_RC_MODE=session` now runs the server in `worktree` mode.
- Each conversation that the server starts receives the environment of the start
  process and starts in the `auto` permission mode. As a result, each
  conversation has the Coder user secrets, the git credentials, and access to
  the credential store.
- The claude.ai service deletes the sessions of a server approximately four
  hours after the server stops. The transcripts stay on the home volume, and
  `claude --resume <id> --remote-control` starts each again as a new claude.ai
  session.
