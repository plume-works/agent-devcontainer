---
type: adr
stage: proposed
supersedes:
- adr/0037-ai-review-trusts-named-bots
- adr/0069-trusted-bot-approval-checks-push-history
---

# The required approval is the only gate of the AI review

Nothing requires an AI review before a merge. The ruleset's required approval is
the gate, and an approval by the AI reviewer counts toward it like any other.
The pull requests of trusted bots are approved without a review.

## Considered Options

- A required check that passes once the AI reviewer has reviewed. Rejected: a
  required check is read on the head commit only, so each push would need a new
  review.
- A ruleset bypass for trusted bots. Rejected: auto-merge ignores a bypass, and
  the merge records no approval.
- Review the pull requests of trusted bots. Rejected: a model run for each
  dependency update.

## Consequences

- A human approval alone is enough to merge.
