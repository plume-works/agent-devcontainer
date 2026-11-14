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

## Consequences

- The prompt of `iwe-revision-evaluator` holds only the plan key and the quoted
  finding. The agent reads `git show HEAD:<plan>` and `git diff -- <plan>`, and
  it has only the `Bash`, `Read`, `Grep`, and `Glob` tools.
- `APPROVE` means that the revision answers the finding and keeps each specified
  behaviour. The session then commits the revision and continues.
- `REJECT` means that the revision does not answer the finding, changes the plan
  to agree with the code, has a hunk that answers no quoted finding, or adds a
  claim that the code must then meet.
- `ESCALATE` means that the revision removes or decreases specified behaviour,
  moves it to a later time, accepts an exception to it, changes `release`, or
  changes text that the user approved.
- On `REJECT` or `ESCALATE`, the session replaces the plan with the plan at
  `HEAD` and stops.
