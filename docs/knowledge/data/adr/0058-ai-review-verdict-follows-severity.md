---
type: adr
stage: accepted
---

# The AI review verdict follows severity alone

The `main` ruleset requires one approving review, keeps stale reviews on push,
and requires every review thread to be resolved. Only an `APPROVE` from the AI
reviewer satisfies that approval and lifts its earlier change request. For this
reason, the verdict is `APPROVE` when the review has no findings or only
non-blocking ones, and `REQUEST_CHANGES` when it has any blocking finding.

## Considered Options

- `COMMENT` when every blocking finding is anchored in an inline thread.
  Rejected: a `COMMENT` neither satisfies the required approval nor lifts the
  earlier change request of the AI reviewer.
- `APPROVE` beside inline blocking findings, relying on thread resolution to
  hold the merge. Rejected: an approval next to an unaddressed blocking finding
  reads as sign-off on it.
- `COMMENT` for every finding, and never `REQUEST_CHANGES`. Rejected: a blocking
  finding then never blocks through the verdict, and no review satisfies the
  required approval.

## Consequences

- The inline threads of a review with the `APPROVE` verdict still hold the merge
  until they are resolved.
- The review uses `COMMENT` only when GitHub refuses a verdict on a pull request
  that the review account owns.
