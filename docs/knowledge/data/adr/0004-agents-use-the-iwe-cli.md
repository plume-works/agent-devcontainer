---
type: adr
stage: accepted
description: Agents read and write the graph through the iwe CLI; the repository registers no IWE MCP server, and the image does not install iwec.
---

# Agents use the iwe CLI, not an IWE MCP server

Each IWE skill and agent uses `iwe` commands from the repository root, so the
tools of an IWE MCP server copied an interface that nothing used. A registered
server also adds its prompts `explore`, `review`, and `refactor` to the slash
command menu of each client. These prompts ignore the schemas of this repository
and have the same names as catalog skills. For this reason, the repository
registers no IWE MCP server, and `dev_tools_pinned_tools` installs `iwe` and
`iwes` but not `iwec`.

## Considered Options

- Keep the server behind a filter that removes its prompts. Rejected: the tools
  that nobody calls stay, and the filter is one more wrapper to maintain.
- Each user disables the server with `disabledMcpjsonServers`. Rejected: each
  workspace and each consumer must disable it, and the default stays wrong.
- Install `iwec` in the image. Rejected: no configuration registers it, so it is
  a binary that nothing uses.

## Consequences

- A skill that needs a graph operation uses the `iwe` CLI. A new skill must not
  use `mcp__iwe__*` tools, because they are not there.
- `iwes`, the language server of the IWE editor extension, stays installed.
- A consumer gets no IWE MCP server by default.
