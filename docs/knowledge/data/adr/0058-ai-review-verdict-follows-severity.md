---
type: adr
stage: accepted
description: The AI review gives APPROVE when it has no finding that blocks the merge and REQUEST_CHANGES when it has one, because only an approval meets the main ruleset.
---

# The AI review verdict follows severity alone

The `main` ruleset requires one approval and keeps a review after a later push.
Only an `APPROVE` from the AI reviewer gives that approval and cancels its
earlier change request. For this reason, the verdict is `APPROVE` when the
review has no finding that blocks the merge, and `REQUEST_CHANGES` when it has
one.

## Considered Options

- `COMMENT` when each blocking finding has an inline thread. Rejected: a
  `COMMENT` does not give the approval and does not cancel an earlier change
  request.
- `APPROVE` with inline blocking findings, and thread resolution to stop the
  merge. Rejected: an approval next to an open blocking finding looks like
  agreement with it.
- `COMMENT` for each finding, and never `REQUEST_CHANGES`. Rejected: a blocking
  finding then never stops the merge through the verdict, and no review gives
  the approval.

## Consequences

- A blocking finding without an inline thread also makes the verdict
  `REQUEST_CHANGES`. The metadata gate is a blocking finding.
- A review that has only findings that do not block is an `APPROVE` with inline
  comments. A review with a blocking finding stops the merge until a later
  review from the same reviewer approves.
- The inline threads of a review with the `APPROVE` verdict stop the merge until
  a person resolves them.
- The review uses `COMMENT` only when GitHub refuses a verdict on a pull request
  that the review account owns. The responder does not review a pull request
  whose author is a bot.
