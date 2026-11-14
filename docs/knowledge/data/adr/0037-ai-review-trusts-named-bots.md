---
type: adr
stage: accepted
description: The AI review gate does not require the AI review for the bot logins in TRUSTED_BOT_ACTORS, and no comment or manual trigger can start the review responder workflow.
---

# The AI review gate trusts only named bots

`.github/workflows/ai-responder.yml#env.TRUSTED_BOT_ACTORS` names each trusted
bot. The AI review gate does not require the AI review for a login on that list
with `user.type` set to `Bot`, and it requires the review for each other author.
The approval job approves only for these logins. The responder never reviews a
pull request from a bot. The workflow has no comment, issue, or
`workflow_dispatch` trigger, so a comment cannot start it.

## Considered Options

- Trust each pull request from `user.type` `Bot`. Rejected: any bot that can
  open a pull request then skips the review.

## Consequences

- Keep `claude-respond` and `ai-review-present` together, or remove both.
- Preflight skips a pull request from a bot, and a pull request whose head is in
  a different repository. The AI review gate still runs for it and finds no
  review. As a result, such a pull request stays blocked, except when its author
  is a trusted bot.
- `ai-review-present` runs on each `pull_request` event, also on a change to a
  label that is not a review label. A job that its own `if:` skips passes a
  required check. If the AI review gate skips, a person who can only add labels
  can make the check pass.
- A consumer edits the list for its own bots and does not add a trigger.
- `claude-respond` and `ai-review-present` stay two jobs. With one job, each run
  that only checks the gate pulls the review container, uses the
  `plume-works-review` environment, and holds the permissions of the review.
  Also, `request-review.py` then cannot tell a review run from a gate run by the
  name of the check.
