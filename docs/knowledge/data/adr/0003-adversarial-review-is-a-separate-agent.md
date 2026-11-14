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
