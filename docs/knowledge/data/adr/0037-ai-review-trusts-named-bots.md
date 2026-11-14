---
type: adr
stage: accepted
description: The `ai-review-present` check does not require the AI review for the bot logins in TRUSTED_BOT_ACTORS, and no comment or manual trigger can start the review responder workflow.
---

# The `ai-review-present` check trusts only named bots

`.github/workflows/ai-responder.yml#env.TRUSTED_BOT_ACTORS` names each trusted
bot. The `ai-review-present` check does not require the AI review for a login on
that list with `user.type` set to `Bot`. It requires the review for each other
author. The approval job approves only for these logins. The `claude-respond`
job never reviews a pull request from a bot. The workflow has no comment, issue,
or `workflow_dispatch` trigger, so a comment cannot start it.

## Considered Options

- Trust each pull request from `user.type` `Bot`. Rejected: any bot that can
  open a pull request then skips the review.

## Consequences

- Keep `claude-respond` and `ai-review-present` together, or remove both.
- `ai-review-present` runs on each `pull_request` event, also on a change to a
  label that is not a review label. A job that its own `if:` skips passes a
  required check. If the `ai-review-present` check skips, a person who can only
  add labels can make the check pass.
- `claude-respond` and `ai-review-present` stay two jobs. With one job, each run
  that only does the `ai-review-present` check pulls the review container. It
  also uses the `plume-works-review` environment and holds the permissions of
  the review. Also, `request-review.py` then cannot tell a review run from a run
  of the `ai-review-present` check by the name of the check.
