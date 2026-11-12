---
type: architecture
description: Why the Implement verify, fix, and revise loop runs in the Implement session, whose every dispatched agent is a leaf, why the Plan rulebook moved into the iwe-planner agent, why a revision is drafted, audited, and evaluated before it commits, and why the loop acts only on what the plan promised.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-revision-evaluator.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
---

# Autonomous Implement loop

## Decision

**The Implement session runs the loop, and every agent is a leaf.** The
Implement session is the session that loaded `/agentdev:iwe-implement`.
`iwe-implementer`, `iwe-verifier`, and `iwe-revision-evaluator` never dispatch,
so the loop runs on Claude Code and OpenCode without OpenCode's experimental
depth setting ([Nested subagent dispatch](nested-subagent-dispatch.md)).

**The loop is written once, in the `iwe-implementer` rulebook,** as
`## Running the loop`, which the Implement session runs as it follows the
rulebook in place.

**The Plan rulebook is the `iwe-planner` catalog agent,** which
`/agentdev:iwe-plan` follows in place, the pattern Implement already uses.
`/agentdev:iwe-plan` is explicit-only, and reading a gated skill's file to get
around the gate is rejected in [Explicit-only workflow
agents](explicit-only-workflow-agents.md). The Implement session follows
`iwe-planner` in its revise mode only, so issue closing — reachable only from
create mode — keeps its script bundled with the skill.

**A revision is drafted, audited, evaluated, then committed.** The Implement
session drafts it under the `iwe-planner` revise rules, including
`/agentdev:iwe-plan-review` — the `Durable Knowledge Auditor`,
`iwe-plan-reviewer`, and
`iwe-ship-reviewer` in plan mode — and validation, and leaves it uncommitted.
`iwe-revision-evaluator` then judges the final text: its prompt carries only the
plan key and the quoted finding, and it reads `git show HEAD:<plan>` and
`git diff -- <plan>`. It returns:

- `APPROVE` — the revision answers the finding and keeps every specified
  behavior; the Implement session commits it and resumes.
- `REJECT` — the revision does not answer the finding, restates the plan to
  match the code, has a hunk that answers no quoted finding, or has a hunk that
  adds or sharpens a claim the code must newly meet.
- `ESCALATE` — the revision drops, narrows, defers, or accepts an exception to
  specified behavior, changes `release`, or changes text the user approved.

On `REJECT` or `ESCALATE` the Implement session restores the plan from `HEAD`
and stops. The evaluator's tools are `Bash, Read, Grep, Glob`.

**The loop acts only on what the plan promised.** Verify is a conformance check:
every CRITICAL and WARNING cites the requirement, scenario, task, or
verification step it contradicts. The loop acts on every CRITICAL, and on a
WARNING only when its fix fits a task the plan already has and adds no claim the
code must newly meet; every other WARNING is filed through
`/agentdev:iwe-capture`. CI belongs to `pr-merge`, which gates every merge on
it, so no plan task claims only that CI passes. Behaviour observable only after
merge is a task carrying a `**Closed by:**` line: Verify lists it as an
outstanding observation rather than a CRITICAL, and Ship, not Verify, refuses
while it is unticked, so Verify's saved report stays the same for both callers.

**The run is bounded.** It stops when a finding recurs after a fix attempt,
after three Verify rounds, or when a second revision would follow one approved
revision.

## Rejected alternatives

- **Let `iwe-verifier` judge the revision.** Verify checks code against the
  plan; whether a new plan still serves the old one's outcome is a different
  question with its own rubric.
- **Reuse `Principal Engineer` as the evaluator.** It is advisory and can
  dispatch agents; the gate needs a leaf that returns a fixed verdict.
- **Evaluate before the audit.** The audit may rewrite the text, so the
  evaluator would approve bytes that never land.
- **Verify treats an observation as CRITICAL only when Ship calls it.** The
  saved report would differ by caller, and Ship reuses the loop's report.
- **Delta-scoped Verify rounds.** They treat the symptom; this decision removes
  its causes, CI timing and unbounded probing, at the source.
- **Run the loop inside a dispatched `iwe-implementer`.** It would need nested
  dispatch, and `iwe-implementer` is never dispatched ([Explicit-only workflow
  agents](explicit-only-workflow-agents.md)).
