---
type: adr
stage: accepted
description: Renovate runs self-hosted from a workflow in the development image and opens pull requests with a GitHub App token.
---

# Renovate runs self-hosted as a GitHub App

`.github/workflows/renovate.yml` runs Renovate in the `agentdev-devcontainer`
image, so the post-upgrade task has the toolchain of a contributor. Renovate
uses a GitHub App token, because a pull request from the `GITHUB_TOKEN` of a
workflow starts no workflow runs. Then CI would not report on it, and automerge
could not occur.

## Considered Options

- The hosted Renovate app. Rejected: it does not run the post-upgrade task in
  the toolchain of a contributor. Next to the self-hosted bot, it would be a
  second Renovate on the same branches.
- `updatecli` or a local refresh loop. Rejected: it is a second dependency
  updater next to Renovate, which owns each pin.
