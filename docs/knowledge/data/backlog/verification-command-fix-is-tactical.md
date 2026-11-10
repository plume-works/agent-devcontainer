---
type: task
created: 2026-11-03
stage: pending
priority: high
description: Treat a corrected `## Verification` command that runs the same check as a tactical correction, so a command broken by its own invocation no longer costs a full revision round.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-revision-evaluator.agent.md
- resource: openspec/specs/iwe-workflow-skills/spec.md
- resource: docs/knowledge/data/plans/20261102-autonomy-loop.md
---

# Fix a broken verification command as a tactical correction

Two rules turn a command that is broken by its own invocation into a full
revision round. `iwe-verifier` reports every failing `## Verification` command
as a CRITICAL, whether the command or the code is at fault. `iwe-implementer`
lists "a corrected verification step" as a material deviation, so the fix takes
the revision route: draft the revision, run the Durable Knowledge Auditor, have
`iwe-revision-evaluator` approve it, then run Verify again. A command such as
`bun test <path>`, which a newer `bun` reads as a name filter until the path
starts with `./`, costs that whole round for a one-character change, and the
implementer that already found the working form may not correct the plan line.
[Make the Implement loop converge](../plans/20261102-autonomy-loop.md) keeps
both rules.

The work: classify a corrected verification step by what it checks.

- **Same check** — the same target and the same pass condition, with only the
  invocation changed (a path form, a flag a tool version renamed, a working
  directory). This becomes a tactical correction: `iwe-implementer` fixes the
  line in the plan in a commit of its own, reports the correction, and Verify
  runs as usual.
- **Different check** — a changed target, a weaker or stronger pass condition,
  or a dropped command. This stays a material deviation, and dropping or
  weakening one stays always-escalate.

Settling it means writing the "same check" test so the planner, implementer,
verifier, and evaluator rulebooks apply it the same way. It also means deciding
whether `iwe-verifier` should run a corrected form it can derive and report the
original command as a WARNING naming that form. The rejected alternative was
leaving the plan's command stale until someone edits it.
