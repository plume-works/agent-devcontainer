---
type: adr
stage: proposed
supersedes:
- adr/0059-ai-reviews-requested-and-held-by-label
---

# A review starts on open or on request, and the request label holds it

Quill reviews a pull request from a branch of the same repository when it opens,
is reopened, or leaves draft, and when a person with write access adds
`request-ai-review`. The label stays on until the review finishes, successful or
failed, and then the service removes it. A push while the label is on cancels
the running review and starts it again on the new head. When a review starts, it
dismisses the previous approval of Quill; a previous change request stays until
the new review posts. While `block-ai-reviews` is on the pull request, or the
service is paused, no review starts.

## Considered Options

- A review on each push. Rejected: a busy pull request costs a model run for
  each push.
- Remove the label when the review starts. Rejected: the label then no longer
  shows that a requested review is still running, and a push could not restart
  it.
- Assign the App or request it as a reviewer. Rejected: GitHub does not allow
  either for a GitHub App.

## Consequences

- A stale approval stops counting toward the merge as soon as a new review
  starts.
