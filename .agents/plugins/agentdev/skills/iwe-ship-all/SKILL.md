---
name: iwe-ship-all
description: Ship all implemented plans in the IWE graph
disable-model-invocation: true
---

# Ship all implemented plans in the IWE graph

You are the coordinator. Discover every active plan whose tasks are all ticked —
implemented but not shipped. Identify their cross dependencies from each plan's
`## Depends on`.

Dispatch the `iwe-shipper` agent once per plan, sequentially, in dependency
order. Each prompt carries only the plan key and the operation `ship`, plus any
approval the user gave when starting this run, quoted verbatim — nothing else
from this conversation. Wait for each report before the next dispatch, and skip
a plan whose dependency did not ship this run.

Re-post each Shipper's Verify verdict and outcome here, one plan per entry,
then a summary of what shipped, what is blocked, and what needs a decision.
