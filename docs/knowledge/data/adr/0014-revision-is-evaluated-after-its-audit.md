---
type: adr
stage: accepted
description: The Implement session writes a plan revision, runs a plan review on it, gets a verdict from iwe-revision-evaluator, and only then commits it.
---

# The Implement session evaluates a plan revision after its plan review, then commits it

The Implement session can continue past a Verify result without the user only
when the revision keeps each specified behaviour of the plan. For this reason,
the session writes the revision, runs `/agentdev:iwe-plan-review` on it, and
then starts `iwe-revision-evaluator` as a subagent. That agent compares the
final text with the plan at `HEAD` and returns `APPROVE`, `REJECT`, or
`ESCALATE`.

## Considered Options

- `iwe-verifier` judges the revision. Rejected: Verify compares code with a
  plan. A comparison of a new plan with the outcome of the old plan is a
  different question with different rules.
- The Principal Engineer agent judges the revision. Rejected: that agent gives
  advice and can start other agents as subagents. The gate needs an agent that
  starts no other agent and returns a fixed verdict.
- The verdict comes before the plan review. Rejected: the plan review can change
  the text, so `iwe-revision-evaluator` approves text that the session does not
  commit.
