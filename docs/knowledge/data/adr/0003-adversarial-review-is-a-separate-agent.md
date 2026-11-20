---
type: adr
stage: accepted
description: Adversarial review runs in its own report-only agent, iwe-adversarial-reviewer, and only on request, never in Verify.
---

# Adversarial review is a separate agent, not part of Verify

Looking for ways to defeat a design or its code asks a different question from a
conformance check, with its own rubric, and its findings have no fixed end. So
it runs in the report-only agent `iwe-adversarial-reviewer`, from a fresh
context, and only when asked.

## Considered Options

- Run it inside every Verify run. Rejected: findings outside the plan's contract
  would keep the Implement session's verify-and-fix loop from converging.
- Make `/agentdev:iwe-adversarial-review` an explicit-only skill. Rejected: the
  Implement session then cannot run a plan task that starts the review.
- Let the `pr-review` skill replace Verify. Rejected: `pr-review` reads only the
  diff and the code that the diff touches, so an unchanged line that a new
  requirement makes wrong is outside its reach. It also does not run the plan's
  verification commands or check task evidence, both of which Ship relies on.

## Consequences

- Verify judges only whether the code conforms to the plan, so behaviour that
  the plan itself specifies can never be a Verify finding, however unsafe. Only
  an adversarial review or a pull request review can find that the specified
  behaviour is wrong.
