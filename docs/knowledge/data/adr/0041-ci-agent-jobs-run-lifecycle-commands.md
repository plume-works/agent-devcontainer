---
type: adr
stage: accepted
description: A CI agent job runs the create, start, and attach phases against its checkout without the supervisor, so the agent uses the catalog of the branch under review.
---

# CI agent jobs run the lifecycle commands against their checkout

A GitHub Actions `container:` job runs no image entrypoint and no Dev Container
lifecycle command, so the supervisor cannot be PID 1 there.
`.github/actions/run-claude-responder/action.yml` runs the create, start, and
attach phases against the checkout, with
`agentdev-runtime lifecycle ready --no-wait`, so the agent uses the skills of
the branch under review. An agent that cannot find a skill does not fail: it
writes a review with no basis, and that review can pass a required check.

## Considered Options

- Use the catalog that the image build installed. Rejected: it has the catalog
  version of the image, not the version of the branch.
- A workflow step that installs the catalog. Rejected: it duplicates the
  lifecycle commands and becomes different from them.
- Start the supervisor in the background in the container job. Rejected: the
  nested `dockerd` needs a privileged job container, and the only gain is to
  remove the `--no-wait` path.
- Run the review responder on a bare runner or as a host job through
  `devcontainers/ci`. Rejected: the review then has no project toolchain, or it
  loses `claude-code-action` and its GitHub App authentication.
- A local copy of the review skill. Rejected: it becomes different from the copy
  in the catalog.
- No `settings` input. Rejected: the project permissions and the model pin go to
  the session only through that input.

## Consequences

- `claude-code-action` merges its `settings` input into the user settings one
  level deep. An `enabledPlugins` in the input replaces the lifecycle value, so
  the action deep-merges the user, project, and local settings first.
- The job sets `AGENTDEV_SKIP_PRE_COMMIT`, because the review never commits and
  the hook installation takes minutes.
- The create phase always marks the checkout a git safe directory, because a CI
  checkout has a different owner UID.
