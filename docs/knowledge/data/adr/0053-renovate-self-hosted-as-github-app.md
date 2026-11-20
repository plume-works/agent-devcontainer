---
type: adr
stage: accepted
description: Renovate runs self-hosted from a workflow in the development image and opens pull requests with a GitHub App token.
---

# Renovate runs self-hosted as a GitHub App

`.github/workflows/renovate.yml` runs Renovate in the `agentdev-devcontainer`
image, so the post-upgrade task has the toolchain of a contributor. Renovate
uses a GitHub App token, because a pull request opened with a workflow's own
`GITHUB_TOKEN` starts no further workflow runs, so CI would never report on it
and automerge could never fire. The App token does start them.

## Considered Options

- The hosted Renovate app. Rejected: it does not run the post-upgrade task in
  the toolchain of a contributor, and next to the self-hosted bot it would be a
  second Renovate contending for the same branches.
- `updatecli` or a repository-local refresh loop. Rejected: it is a second
  dependency updater next to Renovate, which already owns every pin here.

## Consequences

- Each workflow job that runs in the image pins the same digest, and Renovate
  moves each copy in one pull request. As a result, a digest update runs the
  required check of `.github/workflows/validate-renovate-config.yml` in the new
  image before automerge. An image that cannot run the toolchain of the bot
  fails there, not in the next run of the bot.
