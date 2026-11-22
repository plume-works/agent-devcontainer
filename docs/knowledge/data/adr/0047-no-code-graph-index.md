---
type: adr
stage: accepted
---

# The runtime ships no code-graph index

The images, the runtime, and the catalog contain no code-graph daemon, MCP
server, hook, or index. Agents orient with `grep` over the code. The maintainer
removed codebase-memory-mcp because agents never called it unprompted, found the
same code and passed the same tests without it, and cost more and took longer
when told to use it. Its graph also missed virtual C++ dispatch and
cross-package Python calls on untyped receivers.

## Considered Options

- Keep the MCP server opt-in. Rejected: it keeps a pinned binary and its
  upgrades for a tool that no run chose unprompted.
- Require a manual `uninstall` before upgrading. Rejected: anyone who misses the
  step gets a failing hook on every tool call.

## Consequences

- An old installation outlives the image in the home volume, where a hook that
  names the missing binary fails on every tool call, and the tool's own
  `uninstall` is gone with the binary. The create phase therefore clears it, and
  that cleanup stays until no supported instance can still hold one.
