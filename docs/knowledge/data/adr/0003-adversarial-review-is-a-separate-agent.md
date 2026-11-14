---
type: adr
stage: accepted
description: Adversarial review runs in its own report-only agent, iwe-adversarial-reviewer, and only on request, never in Verify.
---

# Adversarial review is a separate agent, not part of Verify

A search for ways to break a design asks a different question from a check of
conformance, and its results have no fixed end. For this reason, it runs in the
report-only agent `iwe-adversarial-reviewer`, from a fresh context, and only on
request. Each result names the claim of the plan that it breaks, or `none`.

## Considered Options

- Add it to the rules of the Durable Knowledge Auditor. Rejected: that agent
  then holds two sets of rules that are not related.
- Run it in each Verify round. Rejected: the Implement loop then gets results
  outside the contract of the plan, and it cannot end.
- Make `/agentdev:iwe-adversarial-review` an explicit-only skill. Rejected: the
  Implement loop then cannot run a plan task that starts the review.
- Let the `pr-review` flow replace Verify. Rejected: `pr-review` reads only the
  diff and the code that the diff changes, so it does not see an unchanged line
  that a new requirement makes wrong. It also does not run the verification
  commands of the plan or examine the evidence of a task, and Ship needs both.

## Consequences

- The review has two targets. The `plan` target looks for claims that the design
  cannot keep, scenarios that the plan does not cover, and limits that a claim
  does not state. The `code` target looks for ways to make the implemented
  behaviour fail.
- `/agentdev:iwe-adversarial-review` dispatches the agent with a prompt that
  holds only the plan key, the target, and the approvals of the user, quoted
  with no change.
- Verify examines only if the code agrees with the plan, so behaviour that the
  plan itself states is never a Verify result. Only an adversarial review or a
  pull request review can find that the specified behaviour is wrong.
- A user can start the review on a plan or on its code. Plan never starts it,
  but a plan can have one task at or near its end that runs the review on the
  code. The Implement session runs that task one time for each plan.
- In that task, a result that names a claim of the plan goes to the code fix
  route. Each other result goes through `/agentdev:iwe-capture`.
