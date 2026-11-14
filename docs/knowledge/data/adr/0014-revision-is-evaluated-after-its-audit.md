---
type: adr
stage: accepted
description: A plan revision in the Implement loop is written, audited, judged by iwe-revision-evaluator, and only then committed.
---

# A plan revision is evaluated after its audit, then committed

The Implement session can continue past a Verify result without the user only
when the revision keeps each specified behaviour of the plan. For this reason,
the session writes the revision, runs `/agentdev:iwe-plan-review` on it, and
then dispatches `iwe-revision-evaluator`. That agent compares the final text
with the plan at `HEAD` and returns `APPROVE`, `REJECT`, or `ESCALATE`.

## Considered Options

- `iwe-verifier` judges the revision. Rejected: Verify compares code with a
  plan. A comparison of a new plan with the outcome of the old plan is a
  different question with different rules.
- The Principal Engineer agent judges the revision. Rejected: that agent gives
  advice and can dispatch agents. The gate needs an agent that starts no other
  agent and returns a fixed verdict.
- The evaluation comes before the audit. Rejected: the audit can change the
  text, so the evaluator approves text that the session does not commit.
