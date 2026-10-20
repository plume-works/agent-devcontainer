---
type: bug
description: CI/CD moves the published tags of ubuntu-ansible, agent-desktop, and agent-opencode before the devcontainer and runtime acceptance jobs test the images, so a failed or cancelled run leaves edge naming an untested build.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-20T03:00:00Z
sources:
- resource: .github/workflows/ci.yml
- resource: .github/workflows/primary-checks.yml
- resource: .github/actions/docker/multiarch-merge/action.yml
- resource: .github/actions/docker/metadata-action/action.yml
- resource: .github/renovate.json
- resource: https://github.com/plume-works/agent-devcontainer/actions/runs/39344687246
---

# Bug: CI/CD publishes images before testing them

## Symptom

`ghcr.io/plume-works/agent-desktop:edge` and `agent-opencode:edge` can name an
image that never passed the devcontainer checks or the runtime acceptance suite.
Renovate then proposes that digest for `devcontainer-compose-pins.yml`, the
workflow job containers, and `opencode-compose-pins.yml`, and pull request
builds reuse it as their warm-start base. The same holds for the `main`,
`pr-<n>`, and release semver tags.

## Reproduction

1. Push a commit to `main` that the image path filter matches.
2. Let `Merge development image` finish, then cancel the run, or let a test job
   fail.
3. The `org.opencontainers.image.revision` label on both `edge` tags names that
   commit, although `Devcontainer image` and `OpenCode runtime acceptance` never
   passed for it.

Primary checks run 39344687246, attempt 3, did this: `Merge development image`
succeeded, and the next push to `main` cancelled both test jobs.

## Root cause

`merge-dev-image` assembles each multi-arch manifest with `multiarch-merge`,
whose `imagetools create` applies every tag `metadata-action` derives for the
event, including `edge` and `main`. `dev-container-ci` and `opencode-acceptance`
need `merge-dev-image`, so they test an image that is already published, and no
step withdraws a tag when they fail or are cancelled.

The design assumed the pull request's tested image and `main`'s rebuild are
equivalent and that one run finishes before the next starts. Neither holds:
`main` rebuilds from a clean `ubuntu:24.04` with unpinned apt packages and
upstream repositories that change between runs, and `primary-checks.yml` cancels
an in-progress run on every push to `main`, which Renovate's automerges make
frequent.

## Fix

Not fixed. The intended shape: per-arch builds and the merge push only an
immutable per-run tag. A promotion job that needs every test job then points the
event's moving tags at those tested digests with `imagetools create`, without
rebuilding. Runs on `main` stop cancelling one another, so `edge` advances
instead of starving.

## Key references

Verified anchor points (line numbers as of 2026-10-20):

- `.github/workflows/ci.yml:182` — `merge-dev-image`, with merge steps at
  `:199`, `:207`, and `:216`
- `.github/workflows/ci.yml:231-233` — `dev-container-ci`, which needs
  `merge-dev-image`
- `.github/workflows/ci.yml:309-311` — `opencode-acceptance`, which needs
  `merge-dev-image`
- `.github/workflows/ci.yml:105-113` — clean builds on `main` and release tags
- `.github/actions/docker/multiarch-merge/action.yml:96` — `imagetools create`
  with every derived tag
- `.github/actions/docker/metadata-action/action.yml:56-59` — `pr`, `semver`,
  and `edge` tag rules
- `.github/workflows/primary-checks.yml:21-23` — `concurrency` with
  `cancel-in-progress: true`

Related: [Bug: Image rebuild lost when a later push to main cancels its
run](main-image-rebuild-lost-on-cancel.md), which keeps a cancelled commit's
image change in the next run's path filter range.
