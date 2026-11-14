---
type: adr
stage: accepted
description: Renovate runs self-hosted from a workflow in the development image and opens pull requests with a GitHub App token.
---

# Renovate runs self-hosted as a GitHub App

`.github/workflows/renovate.yml` runs Renovate in the `agentdev-devcontainer`
image, so the post-upgrade task has the toolchain of a contributor. Renovate
uses a GitHub App token, because a pull request from the `GITHUB_TOKEN` of a
workflow starts no workflow runs. With that token, CI does not report on the
pull request, and automerge cannot occur.

## Considered Options

- The hosted Renovate app. Rejected: it does not run the post-upgrade task in
  the toolchain of a contributor. Next to the self-hosted bot, it is then a
  second Renovate on the same branches.
- `updatecli` or a local update loop. Rejected: it is a second dependency
  updater next to Renovate, which owns each pin.

## Consequences

- Each workflow job that runs in the image pins the same digest, and Renovate
  moves each copy in one pull request. As a result, a digest update runs the
  required check of `.github/workflows/validate-renovate-config.yml` in the new
  image before automerge. An image that cannot run the toolchain of the bot
  fails there, not in the next run of the bot.
