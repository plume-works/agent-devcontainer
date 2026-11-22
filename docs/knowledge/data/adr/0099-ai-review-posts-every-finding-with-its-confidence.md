---
type: adr
stage: accepted
---

# The AI review posts every finding with its Confidence

A validator that drops every finding it cannot confirm hides real issues from
the author, who never learns they were raised. So `pr-review` validation rates
each finding `Confidence: X/10`, from 0 to 10, for how sure the review is that
it is real, and every finding is posted inline with it; the author decides what
a doubtful one is worth. It is always written `Confidence: X/10`, never a bare
number or score, because Confidence measures certainty, not severity: the
verdict still follows the severity tiers alone, as
[ADR-0058](0058-ai-review-verdict-follows-severity.md) records.

## Considered Options

- Post only findings the validator confirms with high confidence. Rejected: a
  real violation the validator calls ambiguous is never seen.
- Post only findings above a Confidence threshold. Rejected: it is the same drop
  at a different line.
- Let Confidence gate the verdict, so only confident blocking findings request
  changes. Rejected: it mixes certainty with severity.
- List low-Confidence findings in the review body instead of inline. Rejected: a
  finding outside a thread is easy to miss and has no place to be answered.

## Consequences

- Every finding opens a thread that holds the merge until resolved; a
  low-Confidence thread can be closed with a reasoned reply.
- A blocking finding requests changes whatever its Confidence, so a doubtful
  blocking finding blocks the merge until its thread is answered.
