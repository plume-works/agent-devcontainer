---
type: spec
description: Rules the repository's GitHub Actions workflows follow — the image build always publishes, so a fork pull request's run fails at the push, and every same-repository action or reusable workflow is referenced with the $/ self-repository syntax that zizmor enforces.
sources:
- resource: .github/workflows/ci.yml
- resource: .github/actions/docker/build-push-action/action.yml
- resource: .github/workflows
- resource: .github/actions
- resource: zizmor.yaml
- resource: .pre-commit-config.yaml
- resource: ansible/roles/dev_tools/defaults/main.yml
- resource: https://docs.zizmor.sh/audits/#self-repository
---

# CI workflows

## Purpose

Defines rules that hold across the repository's GitHub Actions workflows and
composite actions, and that the workflows a consumer inherits carry with them.
What CI publishes and when it promotes a tag belongs to `image-pinning`; the
lint gate belongs to `pre-commit-gate`.

## Requirements

### Requirement: the image build always publishes

`ci.yml`'s image builds SHALL push every image they build to the registry, with
no condition on the head repository, and every job after the build SHALL consume
the images that run published. A pull request from a fork SHALL NOT be made to
pass by building without publishing.

#### Scenario: a pull request from a fork

- **WHEN** CI runs for a pull request whose head repository is a fork
- **THEN** the image build fails at the push, with the fork's read-only token,
  and no later job runs against an image the pull request did not produce

### Requirement: same-repository references use the self-repository syntax

Every `uses:` that refers to an action or reusable workflow in this repository —
in a workflow step, a reusable-workflow call, or a composite action — SHALL
start with `$/`, never `./` and never this repository's `owner/repo/path@ref`.
zizmor's `self-repository` audit SHALL stay enabled in `zizmor.yaml` and run
through the `zizmor` pre-commit hook, and `actionlint` SHALL come from a build
that accepts `$/`.

#### Scenario: a step under always() after a failed checkout

- **WHEN** `log-debug-stats` runs under `if: always()` in a job whose checkout
  failed or was skipped
- **THEN** the action still loads, from the commit that is running

#### Scenario: a workflow adds a local action with ./

- **WHEN** a workflow under `.github/` references a local action as `./...`
- **THEN** the `zizmor` hook fails

## Rationale

### Fork pull requests are not made to pass

The image build is the first stage of CI, not a leaf: the devcontainer
acceptance jobs here, and a consumer's own suites, run inside the image it
published. A fork run that publishes nothing would go green having proved only
that the Dockerfiles compile. An external contribution is therefore run on a
branch in this repository. Fork builds become worth supporting only when a later
stage can consume an image the run produced without a registry write, such as a
runner-local registry, and that has to hold for consumers too.

Rejected:

- **Gating the pushes and everything downstream on a publish verdict.** The
  desktop image would build on the last published base, the devcontainer smoke
  test would run against the committed digest pin, and every later stage here
  and in each consumer needs its own skip — a second CI topology beside the one
  that publishes. The pattern fits a repository whose image build is a leaf.
- **A PAT or `pull_request_target` for fork builds.** Unreviewed code would
  reach the registry; the read-only fork token stays the boundary.

### $/ for same-repository actions

`$/` resolves to the repository at the running commit, so a step needs no
earlier checkout and cannot load an action a previous step wrote to disk, and
GitHub treats it as pinned, which lets a full-SHA pinning policy cover every
action. The loaded content is the same as with `./`, so this is not a security
fix. A job checks out the repository only when a step reads the working tree.
The syntax needs github.com runners v2.336.0 or newer, so a consumer on GitHub
Enterprise Server or older self-hosted runners cannot adopt these workflows
unchanged.

Rejected:

- **Keeping `./` and disabling the zizmor audit.** Leaves every local action
  dependent on a prior checkout and blocks the pinning policy.
- **`owner/repo/path@sha` references.** Pins each reference to a commit other
  than the one running, so an action and its caller cannot change together.
