---
type: someday
description: Ship archives an ADR when each plan that links it is shipped. Then the squash commit of each pull request is the permanent record of the decision.
sources:
- resource: docs/knowledge/data/adr/0002-decisions-are-adrs-in-the-graph.md
- resource: docs/knowledge/SCHEMA.md
---

# Archive ADRs when their plans ship

The user wants the git history to be the permanent record of a decision. Code is
the first source of an answer, and the git history is the second. A document, an
ADR too, is the last source, and a reader must not trust it fully. The text of a
document becomes incorrect when nobody maintains it, but the code and its
history stay correct.

In this idea, Ship moves an ADR to the archive when each plan that links it in
its `## ADRs` section has shipped. After that, the squash commit of each pull
request, whose message is the pull request body, holds the decision. This
replaces [Each decision is a short ADR in the
graph](../adr/0002-decisions-are-adrs-in-the-graph.md).

## Promotion criteria

Promote this idea to a plan when the pull request bodies of shipped plans state
each ADR decision and its reason. Then the archive removes no information from
the git history.
