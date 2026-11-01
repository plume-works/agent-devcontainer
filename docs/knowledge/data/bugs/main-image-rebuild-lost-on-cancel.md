---
type: bug
stage: done
description: A push to main that cancels an in-progress Primary checks run drops the cancelled commit's image rebuild, so agent-desktop:edge stays built from an older commit.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T19:00:00Z
sources:
- resource: .github/workflows/primary-checks.yml
- resource: .github/workflows/ci.yml
- resource: .github/actions/paths-filter/action.yml
- resource: https://github.com/plume-works/agent-devcontainer/pull/328
- resource: scripts/tests/test_paths_filter_last_pass.py
- resource: https://github.com/plume-works/agent-devcontainer/actions/runs/38624887579
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
runs `dorny/paths-filter` with `base: main`; on a push to that same branch,
dorny compares only against the previous push (`github.event.before`). The
surviving run therefore sees only the later commit's files, finds no image path,
and skips the image jobs. Nothing records that the cancelled commit's image
change is still unbuilt. Every workflow that uses the shared `paths-filter`
action and cancels in-progress runs on `main` drops checks the same way.

## Fix

On a push to its base branch, the shared `paths-filter` action looks up the head
commit of the calling workflow's last successful `push` run on that branch and
filters from there. Commits whose runs were cancelled or failed stay inside the
compared range until a run passes. When there is no earlier passing run, or the
lookup fails, the action warns and falls back to the previous push. Every job
that runs the action, and each `primary-checks.yml` job that calls a reusable
workflow running it, grants `actions: read` for the lookup.
`scripts/tests/test_paths_filter_last_pass.py` covers the lookup.

## Key references

Verified anchor points (line numbers as of 2026-10-14):

- `.github/workflows/primary-checks.yml:21-23` — `concurrency` with
  `cancel-in-progress: true`
- `.github/actions/paths-filter/action.yml:67-86` — `last-pass`, the lookup of
  the last passing push run
- `.github/actions/paths-filter/action.yml:88-93` — `filter-base`, filtering
  from `last-pass` or the base branch
- `.github/workflows/ci.yml:67` — image job gate on the filter or `force_run`

## Verification

The fix merged as #336 (`5b92e03`). Three pushes to `main` followed, each
cancelling the run before it: `5b92e03`, Renovate's pin bump `c5fdeff`, and
#337's plan-only `92a2614`. With no passing run among them, each run's
`CI/CD / Need to run?` logged
`Changes will be detected between 296ce39 and main` and raised no warning, so
the image jobs ran for the pin-only and plan-only commits too. Primary checks
run 38624887579 for `92a2614` passed and published `agent-desktop:edge` with
revision `92a2614`, carrying the change `5b92e03` made under `.github/actions/`.
