---
type: adr
stage: accepted
---

# CI agent jobs run the lifecycle commands against their checkout

A GitHub Actions `container:` job runs no image entrypoint, accepts no
`--entrypoint`, and runs no Dev Container lifecycle command, and
`claude-code-action` is a composite action that runs in the job's own runtime,
so the supervisor can never be PID 1 there. The job needs the checkout's
catalog, never the keyring, the firewall, or a desktop.
`.github/actions/run-claude-responder/action.yml` runs the create, start, and
attach phases against the checkout, with
`agentdev-runtime lifecycle ready --no-wait`, so the skill the agent uses is the
one on the branch under review: a pull request that changes a skill is reviewed
by the skill as changed. An agent whose skill does not resolve improvises rather
than fails, so a missing catalog would pass a required review check on an
ungrounded review.

## Considered Options

- Use the catalog that the image build installed. Rejected: it carries the
  image's pinned catalog version, not the branch under review.
- A workflow step that installs the catalog. Rejected: it duplicates what the
  lifecycle commands own and drifts from them.
- Start the supervisor in the background in the container job. Rejected: the
  profile's core `dockerd` needs a privileged job container, and the only gain
  is the removal of the `--no-wait` path.
- Run the review responder on a bare runner, or as a host job through
  `devcontainers/ci`. Rejected: a bare runner gives up the project toolchain
  (`uv`, `bun`, the linters) that grounds a review, and a host job loses
  `claude-code-action` and the GitHub App authentication it carries.

## Consequences

- `claude-code-action` merges its `settings` input into the user settings one
  level deep. An `enabledPlugins` in the input replaces the lifecycle value, so
  the action deep-merges the user, project, and local settings first. This
  repository's own local-scope settings would hide that loss; only a consumer
  repository shows it.
- The job needs all three phases. The attach phase installs the catalog of the
  checkout, so without it the review uses the catalog of the image.
- A container job applies neither the `containerEnv` nor the `mounts` of
  `devcontainer.json`. For this reason, the job sets `DEV_WORKSPACE_FOLDER` and
  `UV_PROJECT_ENVIRONMENT`, and makes `/root/.claude`, before the create phase.
- Without `UV_PROJECT_ENVIRONMENT`, `uv sync` does not fail. It writes `.venv`
  into the checkout under review, and the job still passes.
- The lifecycle commands are a CI contract, not only a Dev Container one. They
  must tolerate the missing mounts of `devcontainer.json` and the missing
  supervisor in a `container:` job.
