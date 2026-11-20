---
type: adr
stage: accepted
description: Agents read and write the graph through the iwe CLI; the repository registers no IWE MCP server, and the image does not install iwec.
---

# Agents use the iwe CLI, not an IWE MCP server

Every IWE skill and agent in the catalog drives the graph through `iwe` commands
run from the repository root, so the tools of an IWE MCP server duplicated an
interface that nothing used. A registered server also adds its prompts
(`explore`, `review`, `refactor`) to every client's slash-command menu. Those
prompts are generic graph dumps that ignore this repository's schemas and
conventions, and their names collide with the catalog's own IWE skills. So the
repository registers no IWE MCP server, and the image does not install `iwec`.

## Considered Options

- Keep the server behind a filter that strips its prompts. Rejected: that keeps
  the tools nobody calls, and the filter becomes a wrapper to maintain.
- Disable the server per user with `disabledMcpjsonServers`. Rejected: every
  workspace and every consumer would need to opt out separately, and the default
  would stay wrong.
- Keep installing `iwec` in the image. Rejected: with nothing registering it,
  the binary is dead weight.

## Consequences

- A skill that needs a graph operation calls the `iwe` CLI. A new skill must not
  assume that `mcp__iwe__*` tools exist.
