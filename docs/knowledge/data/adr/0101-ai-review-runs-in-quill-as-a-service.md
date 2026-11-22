---
type: adr
stage: proposed
supersedes:
- adr/0099-responder-runs-on-pull-request-and-review-events
- adr/0041-ci-agent-jobs-run-lifecycle-commands
---

# The AI review of this repository runs in quill-as-a-service

This repository has no AI review workflow. The Quill GitHub App's webhooks reach
quill-as-a-service, which reviews the pull requests of the repositories in its
configuration, this one included. The workflow kept a copy of itself, its
actions, an environment, and secrets in each repository, and replayed the Dev
Container lifecycle from the pull request's checkout in each review; the service
holds the App key and the Claude token once and reviews with a pinned catalog.

## Consequences

- No pull request runs code of its own to set up its reviewer, so the fork and
  write-access checks no longer guard a token in a job that runs that code.
- The `plume-works-review` environment and its secrets leave the repository.
