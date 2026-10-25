---
type: task
created: 2026-10-25
stage: planned
priority: high
description: Let Implement run Verify itself, act on its findings, and revise its own plan after a fresh-context evaluator approves the revision, escalating to the user only for narrowing, dropping, or release changes.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-25T18:10:00Z
sources:
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
- resource: docs/knowledge/data/features/verification-in-the-main-loop.md
---

# Let Implement verify, fix, and revise on its own

Implement today ends by suggesting `/agentdev:iwe-verify`, and stops for the
user at every material deviation. The user decided Implement should run Verify
itself, act on the report, and revise the plan without them when an independent
evaluator approves the revision first. This is the second of two plans and
depends on [Run Verify from a fresh context](verify-in-fresh-context.md).

## Decisions

- **The orchestrator runs the loop; agents stay leaves.** The user's session
  orchestrates `/agentdev:iwe-implement`, and the coordinator orchestrates
  `/agentdev:iwe-implement-all`. Both are in scope. Neither `iwe-implementer`,
  `iwe-verifier`, the planner, nor the evaluator dispatches another agent
  ([Nested subagent dispatch](../architecture/nested-subagent-dispatch.md)).
- **Loop.** After the tasks, dispatch `iwe-verifier`. Zero CRITICAL ends the run
  with a suggestion to ship. A code or evidence finding is fixed and verified
  again. A finding about intent, or a material deviation, becomes a drafted plan
  revision that a fresh-context evaluator judges before it is committed.
- **Findings acted on.** Every CRITICAL, and every WARNING with a concrete
  route. SUGGESTIONs go to the report only.
- **Bound.** Stop when a finding recurs after a fix attempt, and in any case
  after 3 Verify rounds or 1 approved revision per run.
- **Evaluator scope.** Its inputs are the plan at `HEAD`, the uncommitted
  revision diff, and the Verify report, and nothing from the conversation. It
  answers whether the revision responds to a reported finding while keeping the
  plan's outcome, rather than restating the plan to match the code. It may
  approve corrections, added tasks, a heavier `## Spec changes` form, and
  verification fixes. Dropping or narrowing specified behavior, or changing
  `release`, always escalates to the user. A rejection reverts the diff and
  stops the run with a report.
- **Revision rulebook.** `/agentdev:iwe-plan` is explicit-only, and reading its
  file to get around the gate is rejected in [Explicit-only workflow
  agents](../architecture/explicit-only-workflow-agents.md). Its rulebook moves
  into a planner catalog agent that the plan skill follows in place, and that
  Implement becomes a named starter for. The Durable Knowledge Auditor gate and
  validation still run on every revision.

## Recorded decisions this reverses

- "Implement does not gain a second automatic invocation" in [Verification in
  the main loop](../features/verification-in-the-main-loop.md).
- Implement "waits for user direction" on a material deviation, in [IWE workflow
  skills](../spec/iwe-workflow-skills.md), and the starter list in its
  explicit-only requirement.
