---
type: someday
description: Measure how often iwe-revision-evaluator approves a plan revision a human reviewer would reject, once a named hypothesis about a missed revision class gives the measurement a question to answer.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-27T14:00:44Z
sources:
- resource: .agents/plugins/agentdev/agents/iwe-revision-evaluator.agent.md
- resource: scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py
---

# Calibrate the revision evaluator against human review

In the [Autonomous Implement
loop](../architecture/autonomous-implement-loop.md), an `APPROVE` from
`iwe-revision-evaluator` is the only check before the orchestrator commits a
plan revision with no user in the loop. A false `APPROVE` is the costly error,
because the plan then specifies whatever the revision says. The e2e suite checks
two drafted revisions — a narrowing that must `ESCALATE` and a restatement that
must `REJECT` — and no approval at all against a human verdict.

Measuring the false-approval rate means a corpus of drafted revisions, each with
a human verdict, run through the evaluator. That corpus is the second product
the repository `AGENTS.md` warns against unless a question needs it.

## Promotion criteria

Promote to a backlog task when one of these names a hypothesis the corpus could
confirm or kill:

- A shipped revision the evaluator approved is later found to have dropped,
  narrowed, or re-worded specified or approved behavior. That revision is the
  first corpus entry, and its class is the hypothesis.
- A change to the evaluator's rulebook or model needs evidence that it does not
  approve more revisions a human would reject.

With neither, it stays here; that is a decision, not a lapse.
