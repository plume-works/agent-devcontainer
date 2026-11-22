---
type: adr
stage: proposed
---

# quill-as-a-service is a webhook service and a separate reviewer image

`plume-works/quill-as-a-service` builds two images. The service image, built
from `ghcr.io/plume-works/core-systemd` and run under sysbox, takes the webhooks
of the Quill GitHub App, decides, and runs one reviewer container for each
review on its nested engine. The reviewer image, built from
`ghcr.io/plume-works/core`, carries the `agentdev` plugin and the reviewer
settings, with the catalog pinned in its Dockerfile, and reviews one pull
request head. The service acts only for repositories that its configuration
lists and that have the App installed. The service is TypeScript on Bun with
Octokit.

## Considered Options

- The service mounts the catalog into a plain `core` container. Rejected: it
  couples the service to what the reviewer runs; the plugin and settings belong
  in the reviewer image.
- The catalog comes from the pull request under review, or from its base branch.
  Rejected: a pull request must not choose the rules of its own reviewer, and a
  repository without a catalog copy could not be reviewed.
- Polling the App's installations, or a webhook relay. Rejected: polling adds
  lag, rate-limit cost, and state diffing; a relay puts a third party in front
  of the review.
- Python with `uv`. Rejected: Octokit covers webhook signatures, installation
  tokens, and pagination first-hand, and the rules of `review-gate.js` port
  directly.

## Consequences

- A change to the review rules reaches reviews only through a new pin of the
  catalog in the reviewer image. A pull request that edits `pr-review` is
  reviewed under the pinned rules.
- Installing the App on a repository does nothing until the service
  configuration lists the repository.
