---
type: adr
stage: accepted
description: The Implement session writes a plan revision, runs a plan review on it, gets a verdict from iwe-revision-evaluator, and only then commits it.
---

# The Implement session evaluates a plan revision after its plan review, then commits it

The Implement session may continue past a Verify finding without the user only
when the plan revision keeps every specified behaviour of the plan. So the
session drafts the revision, runs `/agentdev:iwe-plan-review` on it, and then
dispatches `iwe-revision-evaluator` from a fresh context. That agent judges the
final, reviewed text against the plan at `HEAD` and returns a fixed verdict:
`APPROVE`, `REJECT`, or `ESCALATE`.

## Considered Options

- Let `iwe-verifier` judge the revision. Rejected: Verify checks code against
  the plan. Whether a new plan still serves the old plan's outcome is a
  different question with its own rubric.
- Reuse the Principal Engineer agent as the evaluator. Rejected: it is advisory
  and can dispatch agents. The gate needs an agent that dispatches nothing and
  returns a fixed verdict.
- Evaluate before the plan review. Rejected: the review may rewrite the text, so
  `iwe-revision-evaluator` would approve text that never lands.
