---
name: iwe-implement
description: Execute an active plan task-by-task with state discipline — verified anchors, tests before checkbox ticks, clean stopping points, deviations written back into the plan.
disable-model-invocation: true
---

# Implement a plan

The Implement rulebook is the `iwe-implementer` catalog agent. Run it here, in
this session, so you can ask the user about an ambiguous plan or a material
deviation and wait for the answer.

Read [the iwe-implementer rulebook](../../agents/iwe-implementer.agent.md) in
full and follow it in place for the plan the user named, in its
**In the user's session** mode. Do not dispatch it as a subagent: only
`/agentdev:iwe-implement-all` does that.
