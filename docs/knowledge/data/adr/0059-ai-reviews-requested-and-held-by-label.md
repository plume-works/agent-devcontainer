---
type: adr
stage: accepted
description: The request-ai-review label is the one way to request an AI review, and the block-ai-reviews label stops all reviews of a pull request while it is on.
---

# A label requests an AI review and a label stops it

A label change is a `pull_request` event, so the checks of its run attach to the
head commit and count toward the merge. For this reason, `request-ai-review` is
the one way to request an AI review. `block-ai-reviews` stops each review of the
pull request while it is on, which saves the review runs that would fail while
Claude is unavailable.

## Considered Options

- Request a reviewer again. Rejected: an author cannot request their own review,
  so it needs a second collaborator, and it leaves reviewer churn on the pull
  request.
- A comment trigger. Rejected: a run that a comment starts is not a
  `pull_request` run, so its `ai-review-present` check does not count toward the
  merge, and it needs free-form comment parsing.
- A waiver of `ai-review-present` for a person with write access who adds the
  label. Rejected: it keeps the waiver and only narrows who holds it, so a
  writer can merge unreviewed work with no trace in the branch-protection
  record. A ruleset bypass gives the same result through a permission that
  GitHub records.

## Consequences

- The review job removes `request-ai-review` with the App token after the Claude
  step, when the review passes and when it fails. The next push then does not
  start the failed review again. A cancelled review does not remove the label,
  so the run that replaced it reviews the request.
- Only the addition of `request-ai-review` and the removal of `block-ai-reviews`
  join the `pr-<n>` concurrency group. Each other label event has its own group,
  so it never replaces a review that waits in `pr-<n>`.
- The preflight job of the AI review workflow reads the labels from the API, not
  from the event, so a label that a person adds immediately after the pull
  request opens still counts.
- GitHub sends no event when a person adds a label that is already on the pull
  request. For this reason, `pr-request-ai-review` removes and adds the label
  again when no unfinished run will take it.
- `block-ai-reviews` never removes the requirement of `ai-review-present`. It
  only stops new reviews.
- A push starts a review only when the pull request has no accepted AI review:
  an approval, a change request, or a comment of the AI reviewer on a commit of
  the pull request. After an accepted review, a push does not start a review,
  and a person adds `request-ai-review` to get a new review.
