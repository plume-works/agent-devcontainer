---
type: architecture
description: Agents reach the IWE graph through the iwe CLI only; the repository registers no IWE MCP server and the image does not install iwec.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-15T00:00:00Z
sources:
- resource: .mcp.json
- resource: ansible/roles/dev_tools/defaults/main.yml
---

# IWE through the CLI, not MCP

## Decision

Agents read and write the knowledge graph with the `iwe` CLI. `.mcp.json`
registers no IWE MCP server, and the `dev_tools` role installs `iwe` and `iwes`
from the release tarball but not `iwec`. The project owner made this decision.

## Why

Every IWE skill and agent in the catalog drives the graph through `iwe` commands
run from the repository root, so the MCP tools duplicated an interface nothing
used. A registered server also adds its prompts (`explore`, `review`,
`refactor`) to every client's slash-command menu. Those prompts are generic
graph dumps that ignore this repository's schemas and conventions, and their
names collide with the catalog's own IWE skills.

## Rejected alternatives

- **Keep the server behind a filter that strips its prompts.** That keeps the
  tools nobody calls, and the filter becomes a wrapper to maintain.
- **Disable it per user with `disabledMcpjsonServers`.** Every workspace and
  every template consumer would need to opt out separately, and the default
  would stay wrong.
- **Keep installing `iwec`.** With nothing registering it, the binary is dead
  weight in the image.

## Consequences

- A skill that needs a graph operation calls the `iwe` CLI; a new skill must not
  assume `mcp__iwe__*` tools exist.
- `iwes`, the LSP server behind the IWE editor extension, is unaffected.
- Template consumers lose the `iwe` entry from `.mcp.json` on their next
  template update.
