---
name: iwe-implement-all
description: Implement all active plans in the IWE graph
disable-model-invocation: true
---

# Implement all active plans in the IWE graph

You are the coordinator. Discover all active plans. Identify their cross
dependencies from each plan's `## Depends on`.

Dispatch the `iwe-implementer` agent once per plan, sequentially, in dependency
order, with the plan key as its prompt. Allow each to load `AGENTS.md` or
`CLAUDE.md` for guidance. Wait for each report before the next dispatch; a
plan whose dependency is not yet `stage: done` stops at its own dependency
check.

Re-post each Implementer's final rollup here, including any decision it
stopped for.
