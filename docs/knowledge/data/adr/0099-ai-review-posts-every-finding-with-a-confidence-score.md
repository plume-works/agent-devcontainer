---
type: adr
stage: accepted
description: The AI review posts every finding it raises with a 0–10 confidence score instead of dropping the ones its validator cannot confirm, and the score never changes the verdict.
---

# The AI review posts every finding with a confidence score

A validator that drops every finding it cannot confirm hides real issues from
the author, who never learns they were raised. So `pr-review` validation scores
each finding from 0 to 10 for how sure the review is that it is real, and every
finding is posted inline with its score; the author decides what a doubtful one
is worth. The score measures certainty, not severity: the verdict still follows
the severity tiers alone, as
[ADR-0058](0058-ai-review-verdict-follows-severity.md) records.

## Considered Options

- Post only findings the validator confirms with high confidence. Rejected: a
  real violation the validator calls ambiguous is never seen.
- Post only findings above a score threshold. Rejected: it is the same drop at a
  different line.
- Let the score gate the verdict, so only confident blocking findings request
  changes. Rejected: it mixes certainty with severity.
- List low-score findings in the review body instead of inline. Rejected: a
  finding outside a thread is easy to miss and has no place to be answered.

## Consequences

- Every finding opens a thread that holds the merge until resolved, including
  low-score and blocking ones; a low-score thread can be closed with a reasoned
  reply.
