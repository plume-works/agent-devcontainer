---
type: adr
stage: accepted
---

# The `ai-review-present` check trusts only named bots

`.github/workflows/ai-responder.yml#env.TRUSTED_BOT_ACTORS` names each trusted
bot. The `ai-review-present` check waives the AI review only for a login on that
list, matched exactly, and only when `user.type` is `Bot`. It requires the
review for every other author. The approval job approves only for these logins.
The `claude-respond` job never reviews a pull request from a bot. The workflow
has no comment, issue, or `workflow_dispatch` trigger, so a comment cannot start
it.

## Considered Options

- Trust each pull request from `user.type` `Bot`. Rejected: any bot that can
  open a pull request then skips the review.

## Consequences

- Keep `claude-respond` and `ai-review-present` together, or remove both.
- `ai-review-present` runs on each `pull_request` event, also on a change to a
  label that is not a review label. A job skipped by its own `if:` satisfies a
  required check, so skipping `ai-review-present` for an unrelated label would
  let anyone with triage access turn it green.
- `claude-respond` and `ai-review-present` stay two jobs. Merged into one, every
  run that only checks for a review would also pull the review container, take
  the `plume-works-review` environment, and hold the review's write permissions,
  and `request-review.py` could no longer tell a reviewing run from a check-only
  one by the check name.
