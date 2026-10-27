---
name: iwe-implement
description: Execute an active plan task-by-task with state discipline — verified anchors, tests before checkbox ticks, clean stopping points, deviations written back into the plan — then verify the result and act on the findings.
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

This session is the orchestrator, so it also runs the rulebook's
`## Running the loop`: it dispatches `iwe-verifier`, acts on the findings, and
takes an evaluated revision without asking. Ask the user only for an
always-escalate deviation, a Verify `Needs decision`, or a stop bound.
