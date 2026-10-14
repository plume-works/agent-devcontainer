---
type: bug
description: A push to main that cancels an in-progress Primary checks run drops the cancelled commit's image rebuild, so agent-desktop:edge stays built from an older commit.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-13T16:10:00Z
sources:
- resource: .github/workflows/primary-checks.yml
- resource: .github/workflows/ci.yml
- resource: .github/actions/paths-filter/action.yml
- resource: https://github.com/plume-works/agent-devcontainer/pull/328
---

# Bug: Image rebuild lost when a later push to main cancels its run

## Symptom

A commit on `main` that changes an image path (`.devcontainer/`, `ansible/`, the
catalog, and the other `image` filter paths) never gets an `agent-desktop:edge`
build when another commit lands on `main` before its Primary checks run
finishes, and that later commit touches no image path. The `edge` tag keeps the
digest built from an older commit, and Renovate's automerged pin bump moves
`devcontainer-compose-pins.yml` to that stale image.

## Reproduction

1. Merge a pull request that changes an image path, such as
   `ansible/roles/install_docker/tasks/main.yml`.
2. Before its Primary checks run on `main` finishes the image jobs, merge a
   change that touches no image path — a Renovate pin or dependency bump.
3. The first run ends `cancelled`. The second run's `CI/CD / Need to run?`
   passes, but `Development image`, `Merge development image`, and
   `Devcontainer image` are `skipped`. The `org.opencontainers.image.revision`
   label on `agent-desktop:edge` still names a commit before step 1.

PR #328 followed by Renovate's #329 and #330 hit exactly this: `edge` stayed at
revision `c4463c5`, the commit before #328.

## Root cause

Primary checks runs in the concurrency group
`${{ github.workflow }}-${{ github.ref }}` with `cancel-in-progress: true`, so a
second push to `main` cancels the first run. The `CI/CD` path filter for a push
runs `dorny/paths-filter` without a `base-branch`; on a push to the default
branch that compares only against the previous push (`github.event.before`). The
surviving run therefore sees only the later commit's files, finds no image path,
and skips the image jobs. Nothing records that the cancelled commit's image
change is still unbuilt.

## Fix

Unfixed. Running Primary checks by `workflow_dispatch` on `main` forces the
image jobs (`force_run`) and publishes an `edge` built from the current head.

## Key references

Verified anchor points (line numbers as of 2026-10-13):

- `.github/workflows/primary-checks.yml:21-23` — `concurrency` with
  `cancel-in-progress: true`
- `.github/workflows/ci.yml:48-51` — path filter called without `base-branch`
- `.github/actions/paths-filter/action.yml:65-71` — `filter-base`, the
  non-pull-request filter
- `.github/workflows/ci.yml:66` — image job gate on the filter or `force_run`
