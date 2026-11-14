---
type: adr
stage: accepted
description: No Dev Container lifecycle command starts Remote Control; the agent start does, and a runtime supervisor does only when AGENTDEV_CLAUDE_RC_MODE is set.
---

# No Dev Container lifecycle command starts Remote Control

In a Coder workspace, the start phase always runs before the Coder agent exists.
As a result, the agent start `agentdev-runtime coder start` starts Remote
Control, and no Dev Container lifecycle command starts it. A runtime supervisor
also starts it as an opt-in client, but only when `AGENTDEV_CLAUDE_RC_MODE` is
set
(`py_packages/agentdev_runtime/agentdev_runtime/supervisor.py::enabled_services`).

## Considered Options

- A start-phase entry next to the agent-start entry, where one entry gives
  priority to the other. Rejected: the start-phase entry must then see a Coder
  signal that does not exist yet. If not, the agent start must stop a live
  session that it did not start.
