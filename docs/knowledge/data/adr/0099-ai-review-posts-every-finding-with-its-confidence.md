---
type: adr
stage: accepted
description: 'The AI review posts every finding it raises with its `Confidence: X/10` instead of dropping the ones its validator cannot confirm, and Confidence never changes the verdict.'
---

# The AI review posts every finding with its Confidence

A validator that drops every finding it cannot confirm hides real issues from
the author, who never learns they were raised. So `pr-review` validation rates
each finding `Confidence: X/10`, from 0 to 10, for how sure the review is that
it is real, and every finding is posted with it: inline, or in the review body,
named by anchor, when it quotes no added line. The author decides what a
doubtful one is worth. It is always written `Confidence: X/10`, never a bare
number or score, because Confidence measures certainty, not impact: the verdict
follows the finding's Severity alone, as
[ADR-0100](0100-ai-review-verdict-follows-p1-severity.md) records.

## Considered Options

- Post only findings the validator confirms with high confidence. Rejected: a
  real violation the validator calls ambiguous is never seen.
- Post only findings above a Confidence threshold. Rejected: it is the same drop
  at a different line.
- Let Confidence gate the verdict, so only confident findings request changes.
  Rejected: it mixes certainty with impact.
- List low-Confidence findings in the review body instead of inline. Rejected: a
  finding outside a thread is easy to miss and has no place to be answered.

## Consequences

- Every inline finding opens a thread that holds the merge until resolved; a
  low-Confidence thread can be closed with a reasoned reply. A finding in the
  review body opens no thread and holds the merge only through the verdict.
- A `Severity: P1` finding requests changes whatever its Confidence. Answering
  its thread does not lift that verdict; only a fresh review of a later head
  does.
