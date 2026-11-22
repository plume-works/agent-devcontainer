---
type: adr
stage: accepted
description: 'Every AI review finding carries `Severity: P1`, `P2`, or `P3` by its impact, and only a P1 finding makes the review request changes.'
supersedes:
- adr/0058-ai-review-verdict-follows-severity
---

# The AI review verdict follows P1 severity

The `main` ruleset requires one approving review and every review thread
resolved, and only an `APPROVE` from the AI reviewer meets that approval. Each
`pr-review` finding carries `Severity: P1`, `Severity: P2`, or `Severity: P3`,
set by the harm it does if the pull request merges as it is, never by which pass
raised it. The verdict is `REQUEST_CHANGES` when any finding is P1, and
`APPROVE` otherwise; the open thread of a P2 or P3 finding still holds the merge
until it is resolved. A P2 or P3 finding is by definition not one the approval
withholds sign-off on, so an approval beside it signs off nothing it should not.
Confidence never changes Severity or the verdict
([ADR-0099](0099-ai-review-posts-every-finding-with-its-confidence.md)).

## Considered Options

- Severity decided by the raising pass: every correctness or docs finding
  blocks. Rejected: a doubtful or cosmetic finding then requests changes.
- P1 and P2 both request changes. Rejected: a limited-impact finding already
  holds the merge through its thread, and a change request on it adds a
  re-review cycle for no added protection.
