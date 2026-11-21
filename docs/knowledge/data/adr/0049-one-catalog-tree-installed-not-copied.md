---
type: adr
stage: accepted
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
  plugin cache of a consumer (the copy of the plugin that the harness installs
  in the home directory), that location is the cache and not the repository of
  the consumer.
