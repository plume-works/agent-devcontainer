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
- A state label that stays on until the AI reviewer posts the review. Rejected:
  a failed review leaves the label on, and a person must remove it before the
  next request.
- A label for the effort of the review. Rejected: each review sets its own
  effort.
- A pause of all reviews in the repository. Rejected: a `block-ai-reviews` label
  on each pull request covers a time when Claude is not available.
- A marker commit as the request. Rejected: no rule can tell if a review covers
  the marker. A commit ID changes after a rebase, an empty commit has the same
  diff as its parent, and a match on author, date, and message fails when one of
  them changes. Also, each request adds a commit.

## Consequences

- The review job removes `request-ai-review` with the App token after the Claude
  step, when the review passes and when it fails. The next push then does not
  start the failed review again. A cancelled review does not remove the label,
  so the run that replaced it reviews the request.
- Only the addition of `request-ai-review` and the removal of `block-ai-reviews`
  join the `pr-<n>` concurrency group. Each other label event has its own group,
  so it never replaces a review that waits in `pr-<n>`.
- Each run in `pr-<n>` takes a `request-ai-review` that it finds. A request on a
  draft, or from a person without write access, stays until a later run reviews
  it.
- Preflight reads the labels from the API, not from the event, so a label added
  just after the pull request opens still counts.
- While `block-ai-reviews` is on, a `request-ai-review` stays on the pull
  request. The run that the removal of `block-ai-reviews` starts reviews it.
- GitHub sends no event when a person adds a label that is already on the pull
  request. For this reason,
  `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py`
  removes and adds the label again when no unfinished run will take it.
- `block-ai-reviews` never removes the requirement of `ai-review-present`. It
  only stops new reviews.
- A push starts a review only when the pull request has no accepted AI review.
  After an accepted review, a push does not start a review, and a person adds
  `request-ai-review` to get a new review.
