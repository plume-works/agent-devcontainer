---
type: bug
description: A plan checkbox can bundle several independently observed outcomes, so the implementer cannot tick the half it observed and has to park that evidence elsewhere; neither the plan skill's coherence check nor the plan auditor tests checkbox granularity.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-20T20:30:00Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-audit/SKILL.md
- resource: .agents/plugins/agentdev/agents/durable-knowledge-auditor.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: docs/knowledge/data/plans/20261020-gate-image-publication.md
---

# Bug: Plan tasks bundle independent observations

## Symptom

A plan checkbox can require several outcomes that are observed separately, at
different times, by different runs. When one has been observed and another has
not, the implementer has no honest way to record progress. The box cannot be
ticked, because one part is unproven. An unticked box must stay bare, with no
evidence line. The evidence that does exist has to be placed somewhere the
checkbox contract does not name, such as the plan's `## Verification results`,
and the checkbox gives no sign that any part of it is done.

The plan skill already forbids this shape, and the plan passed both of its
gates: the coherence re-read and the fresh-context auditor.

## Reproduction

[Gate image publication on
acceptance](../plans/20261020-gate-image-publication.md), Task 5, has a single
checkbox closed by CI after merge:

> A `main` run promotes `edge` for all three images only after both test jobs
> pass, its revision labels name that run's commit, and a run whose tests fail
> or are cancelled leaves `edge` unchanged.

This checkbox needs two separate observations:

1. A passing `main` run that promotes `edge`, seen on the first run after merge.
2. A failed or cancelled `main` run that leaves `edge` unchanged. This event
   need not ever happen on its own, so it may have to be provoked.

Primary checks run 39482903699 at `441b869` showed the first. Nothing showed the
second. The implementer left the box bare and wrote the first observation under
`## Verification results`, then had to provoke a cancelled run before it could
tick anything.

## Root cause

The rule exists only as prose, and neither gate tests it.

- **Plan rule.** `iwe-plan` says "One task is one outcome; if the task could
  ever be described as half-done, split it", and says a task with external
  evidence stands alone. Task 5 was split from the code tasks as that rule asks.
  But the rule speaks of tasks, not checkboxes. It never says that one
  externally evidenced checkbox must not join several observations, so a single
  "Closed by" box can join two CI events with "and".
- **Coherence check.** Step 6 re-reads the plan for agreement between sections.
  It does not ask, for each checkbox, which single observation closes it.
- **Auditor.** Step 7 dispatches the Durable Knowledge Auditor in plan scope.
  `iwe-audit`'s plan scope collects durable-knowledge residue (provenance,
  defended alternatives, dated tool behavior) and nothing else. Checkbox
  granularity is outside what it examines, so a bundled checkbox always passes.
- **Implementer.** The rulebook is correct to keep a partly evidenced box
  unticked. That correctness is what turns the planning defect into a
  bookkeeping problem at implementation time.

## Fix

Not fixed. The fix direction:

- **`iwe-plan`.** State the rule per checkbox. Each checkbox names exactly one
  observation that closes it. A checkbox whose outcome joins independently
  observable events with "and" is split, one checkbox per event. An event that
  may never occur on its own, such as a failure or cancellation path, names how
  it is provoked. Add the per-checkbox question to step 6's coherence check.
- **Auditor.** Extend `iwe-audit`'s plan scope, or the gate step 7 dispatches,
  to flag a checkbox that bundles more than one independently observed outcome,
  with the recommendation to split it.
- **Outcome.** The implementer can tick each observation as it arrives, without
  finding another section to hold the evidence.

## Key references

Verified anchor points (line numbers as of 2026-10-20):

- `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md:216` — "One task is one
  outcome", and external evidence stands alone
- `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md:121` — step 6, check
  coherence
- `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md:125` — step 7, the
  fresh-context Durable Knowledge Auditor gate
- `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md:41` — plan scope, limited
  to durable-knowledge residue
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:70` — partial work
  stays unchecked, with no evidence line
- `docs/knowledge/data/plans/20261020-gate-image-publication.md:122` — Task 5,
  the bundled checkbox; `:179` — `## Verification results`, where its observed
  half was recorded
