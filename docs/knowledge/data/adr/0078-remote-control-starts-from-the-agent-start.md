---
type: adr
stage: accepted
description: No Dev Container lifecycle command starts Remote Control; the agent start does, and a runtime supervisor does only when AGENTDEV_CLAUDE_RC_MODE is set.
---

# No Dev Container lifecycle command starts Remote Control

In a Coder workspace, the start phase always runs before the Coder agent exists.
As a result, the agent start `agentdev-runtime coder start` starts Remote
Control, and no Dev Container lifecycle command starts it. A runtime supervisor
also starts it, but only when `AGENTDEV_CLAUDE_RC_MODE` is set
(`py_packages/agentdev_runtime/agentdev_runtime/supervisor.py::enabled_services`).

## Considered Options

- A start-phase entry next to the agent-start entry, where one entry gives
  priority to the other. Rejected: the start-phase entry must then see a Coder
  signal that does not exist yet. If not, the agent start must stop a live
  session that it did not start.
- A one-shot component in the supervisor that skips the start when no claude.ai
  login exists. Rejected: an operator must then retry it after the first login,
  and nothing starts a session again after it exits.
- A run of `claude auth status` at each interval. Rejected: each run starts a
  Claude process.

## Consequences

- `agentdev-runtime remote-control start` reads an unset mode as `session`, so
  it cannot tell "off" from the default. For this reason, the supervisor holds
  the gate, and without a mode it does not configure the component.
- In the supervisor, the component is the watcher
  `agentdev-runtime remote-control run`, because the first start usually has no
  login yet. It runs `claude auth status` again only when the inode, the change
  time, or the size of the credential file changes.
- Without a login, the watcher writes that it waits to
  `$XDG_RUNTIME_DIR/remote-control.status` and stays ready.
- Remote Control runs on its own `tmux -L claude-remote` server, outside the
  process group of the watcher. A watcher that starts again uses the live
  session and does not start a second one.
- When a session that the watcher saw stops while the login is valid, the
  watcher exits. The recovery budget of the controller sets how often Remote
  Control starts again.
