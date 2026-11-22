---
type: adr
stage: accepted
supersedes:
- adr/0041-ci-agent-jobs-run-lifecycle-commands
---

# The CI review runs the catalog of its image, not of the checkout

A GitHub Actions `container:` job runs no image entrypoint and no Dev Container
lifecycle command, so the review job of `.github/workflows/ai-responder.yml`
runs the create and start phases itself, with
`agentdev-runtime lifecycle ready --no-wait`. The create phase installs the
catalog the pinned image stages in `AGENTDEV_CATALOG_DIR`. The job runs the
attach phase's project sync and hooks but not `lifecycle attached`, which would
install the checkout's catalog over it, so the review runs the skills of the
image. A pull request that changes `pr-review` is reviewed by the released
skill, not by itself: a skill that grades its own rules finds only the cases
those rules create. A changed skill reviews pull requests once Renovate moves
the image pin.

## Considered Options

- Review with the checkout's catalog, as ADR-0041 did. Rejected: a pull request
  that changes the review skill is reviewed by the change under review.
- Run the whole attach phase, then install the image's catalog again over the
  checkout's. Rejected: two installs, where skipping one gives the same result.
- Start the supervisor in the background in the container job. Rejected: the
  profile's core `dockerd` needs a privileged job container.
- Run the review on a bare runner, or as a host job through `devcontainers/ci`.
  Rejected: a bare runner gives up the project toolchain (`uv`, `bun`, the
  linters), and a host job loses `claude-code-action` and the GitHub App
  authentication it carries.

## Consequences

- `claude-code-action` merges its `settings` input into the user settings one
  level deep. An `enabledPlugins` in the input replaces the lifecycle value, so
  the action deep-merges the user, project, and local settings first.
- A container job applies neither the `containerEnv` nor the `mounts` of
  `devcontainer.json`, so the job sets `DEV_WORKSPACE_FOLDER` and
  `UV_PROJECT_ENVIRONMENT`, and makes `/root/.claude`, before the create phase.
  Without `UV_PROJECT_ENVIRONMENT`, `uv sync` writes `.venv` into the checkout
  under review and the job still passes.
- The lifecycle commands are a CI contract, not only a Dev Container one. They
  must tolerate the missing mounts of `devcontainer.json` and the missing
  supervisor in a `container:` job.
