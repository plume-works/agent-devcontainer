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

You are also each plan's orchestrator. Read `## Running the loop` in [the
iwe-implementer rulebook](../../agents/iwe-implementer.agent.md) and run it
for each plan before the next dispatch. Where it fixes code, re-dispatch
`iwe-implementer` with the plan key and the findings to fix, quoted as
reported, rather than fixing them yourself.

Re-post each plan's rollup here, with each Verify verdict and each evaluator
verdict, and any decision it stopped for.
