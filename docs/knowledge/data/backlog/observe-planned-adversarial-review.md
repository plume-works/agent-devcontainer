---
type: task
created: 2026-11-04
stage: pending
priority: low
description: Observe Implement running a plan's adversarial review task end to end — fixing each finding that defeats a plan claim and filing the rest — on Claude Code and OpenCode, the first time a real plan carries one.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-adversarial-review/SKILL.md
---

# Observe a planned adversarial review task through the Implement loop

No session has been observed to follow the rule in
`.agents/plugins/agentdev/agents/iwe-implementer.agent.md#the-adversarial-review-task`:
the Implement session runs `/agentdev:iwe-adversarial-review <plan> code` once,
takes each finding that names a plan claim down the code route, and files every
other finding through `/agentdev:iwe-capture`.

Until it is observed, a plan that schedules the review can end with the review
run and its findings unhandled while the plan reads as reviewed.

The first time a real plan carries such a task, observe one
`/agentdev:iwe-implement` run on Claude Code and one on OpenCode. Done when each
run shows the review dispatched once, each claim-defeating finding fixed with a
commit, each other finding filed and named in the report, and the task ticked
with that evidence.

Priority is low because no plan carries the task yet.
