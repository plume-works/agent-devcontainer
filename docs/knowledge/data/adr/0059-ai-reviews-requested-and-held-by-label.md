---
type: adr
stage: accepted
description: The request-ai-review label is the one way to request an AI review, and the block-ai-reviews label stops all reviews of a pull request while it is on.
---

# A label requests an AI review and a label stops it

A label change is a `pull_request` event, so the checks of its run attach to the
head commit and count toward the merge. For this reason, `request-ai-review` is
the one way to request an AI review. `block-ai-reviews` stops each review of the
pull request while it is on.

## Considered Options

- Assign the pull request. Rejected: the assignee field means ownership, and a
  new request needs two actions.
- Request a reviewer again. Rejected: an author cannot request their own review,
  so it needs a second collaborator.
- A comment trigger. Rejected: a run that a comment starts is not a
  `pull_request` run, so its `ai-review-present` check does not count toward the
  merge.
- A label that stops reviews, but that an explicit request cancels. Rejected: a
  label that stops reviews and then lets a request start one looks broken.
- A waiver of `ai-review-present` for a person with write access who adds the
  label. Rejected: a writer could then merge work without review, and branch
  protection records nothing. A ruleset bypass gives the same result through a
  permission that GitHub records.

## Consequences

- The review that finishes removes `request-ai-review`.
- `block-ai-reviews` never removes the requirement of `ai-review-present`. It
  only stops new reviews.
