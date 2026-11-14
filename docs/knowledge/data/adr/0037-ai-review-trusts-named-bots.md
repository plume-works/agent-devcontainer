---
type: adr
stage: accepted
description: The AI review gate waives its review only for the bot logins in TRUSTED_BOT_ACTORS, and no comment or manual trigger can start the AI responder.
---

# The AI review gate trusts only named bots

`.github/workflows/ai-responder.yml#env.TRUSTED_BOT_ACTORS` names each trusted
bot. The gate waives the AI review only for a login on that list with
`user.type` set to `Bot`. The approval job approves only for these logins. The
responder never reviews a pull request from a bot. The workflow has no comment,
issue, or `workflow_dispatch` trigger, so a comment cannot start it.

## Considered Options

- Trust each pull request from `user.type` `Bot`. Rejected: any bot that can
  open a pull request then skips the review.

## Consequences

- Keep `claude-respond` and `ai-review-present` together, or remove both.
- A consumer edits the list for its own bots and does not add a trigger.
