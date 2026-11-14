---
type: adr
stage: accepted
description: The images, the runtime, and the catalog ship no code-graph daemon, MCP server, hook, or index, and the create phase removes an old codebase-memory-mcp installation.
---

# The runtime ships no code-graph index

The images, the runtime, and the catalog ship no code-graph daemon, MCP server,
hook, or index. Agents find code with `grep`. Agents did not call
codebase-memory-mcp without an instruction, and they passed the same tests
without it. When an instruction told them to use it, they used more time and
cost. Its graph also missed virtual C++ calls and Python calls on untyped
receivers.

## Considered Options

- Keep the MCP server as an option. Rejected: it keeps a pinned binary and its
  updates for a tool that no run selected without an instruction.
- Tell users to run a manual `uninstall` before the upgrade. Rejected: a user
  who does not do the step has a failed hook on each tool call.

## Consequences

- An old installation stays in the home volume after an image change.
  `agentdev_runtime/cbm_purge.py` removes it in the create phase, until no
  supported instance can have one.
