---
type: adr
stage: accepted
description: The catalog has one source tree, .agents/plugins/agentdev/, that every harness reads and that a consumer runs from the installed plugin.
---

# One catalog tree, installed and not copied

`.agents/plugins/agentdev/` is the one source of the catalog. Claude Code reads
it through `.claude-plugin/marketplace.json`, and OpenCode reads it through the
OpenCode bridge. A consumer runs the catalog from the installed plugin, without
a copy of this repository.

## Considered Options

- A copy of the catalog for each harness. Rejected: two trees must then stay the
  same, and nothing keeps them the same.
- Scripts that find the repository from their own location. Rejected: in the
  plugin cache of a consumer, that location is the cache and not the repository
  of the consumer.
