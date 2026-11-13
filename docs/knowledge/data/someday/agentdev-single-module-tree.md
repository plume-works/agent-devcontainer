---
type: someday
description: Consolidate all agentdev catalog code — the shared bin/ modules and every skill's agent-code scripts — into one proper Python module tree.
sources:
- resource: .agents/plugins/agentdev/bin/
- resource: docs/knowledge/data/archive/2.0.0/architecture/catalog-script-language.md
---

# Consolidate agentdev code into one module tree

The maintainer leans toward a large refactor that merges all agentdev catalog
code into a single module tree. Today the shared modules sit flat in the
plugin's `bin/`, each skill keeps its own scripts in `skills/*/agent-code/`, and
a script reaches `bin/` by inserting it into `sys.path` ([Catalog script
language](../archive/2.0.0/architecture/catalog-script-language.md)).

Until then, new shared catalog code goes in `bin/`, so it moves as one piece.

## Promotion criteria

Promote to a plan once the layout is chosen: the package root, how a skill's
script imports it, and how the plugin test suite resolves it from a consumer's
plugin cache — all within the standard-library, no-install constraints of
[Catalog script
language](../archive/2.0.0/architecture/catalog-script-language.md).
