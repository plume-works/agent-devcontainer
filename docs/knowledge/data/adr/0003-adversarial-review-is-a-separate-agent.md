---
type: adr
stage: accepted
description: Adversarial review runs in its own report-only agent, iwe-adversarial-reviewer, and only on request, never in Verify.
---

# Adversarial review is a separate agent, not part of Verify

A search for ways to break a design asks a different question from a check of
conformance, and its results have no fixed end. For this reason, it runs in the
report-only agent `iwe-adversarial-reviewer`, from a fresh context, and only on
request.

## Considered Options

- Run it in each Verify round. Rejected: the Implement loop then gets results
  outside the contract of the plan, and it cannot end.
- Make `/agentdev:iwe-adversarial-review` an explicit-only skill. Rejected: the
  Implement loop then cannot run a plan task that starts the review.
- Let the `pr-review` flow replace Verify. Rejected: `pr-review` reads only the
  diff and the code that the diff changes, so it does not see an unchanged line
  that a new requirement makes wrong. It also does not run the verification
  commands of the plan or examine the evidence of a task, and Ship needs both.

## Consequences

- Verify examines only if the code agrees with the plan, so behaviour that the
  plan itself states is never a Verify result. Only an adversarial review or a
  pull request review can find that the specified behaviour is wrong.
