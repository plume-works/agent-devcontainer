---
type: adr
stage: accepted
description: The durable-knowledge check runs in an agent that did not see the work and cannot edit the file, with its rule in the one rulebook iwe-audit.
---

# The durable-knowledge audit runs in an isolated agent

Session residue survives because the writer reads its draft through the session
that produced it. So the audit runs in the Durable Knowledge Auditor, an agent
that never saw the work and cannot edit what it reads, and the rule lives in one
rulebook, `iwe-audit`. Every edit to a plan's intent funnels through Plan, so
one gate in `/agentdev:iwe-plan-review` covers create, revise, and every route
back to revise.

## Considered Options

- A self-audit step inside Plan's own context. Rejected: it re-reads the
  polluted context that wrote the draft.
- Each caller inlines the rule into a subagent it spawns. Rejected: the rule
  drifts at every call site.
- Detect narration mechanically in the plan-shape check. Rejected: narration has
  no shape. A length or prose-ratio heuristic fires on long plans and misses a
  short, dense logbook.
