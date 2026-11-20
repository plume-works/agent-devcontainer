---
type: adr
stage: accepted
description: A push to main waits for a cooldown in a job that a newer push cancels, so a burst of merges builds once, and a cap keeps a steady stream of merges from postponing every build.
---

# Pushes to main build after a cooldown that a newer push cancels

Each run of the `Primary checks` workflow on `main` is a full multi-arch build,
and runs on `main` queue rather than cancel once building, so back-to-back
merges would each build in turn. The `cooldown` job in
`.github/workflows/primary-checks.yml` has its own cancel-in-progress group, so
a newer push cancels a run that has not started building, and a burst of merges
builds once. `scripts/ci-cooldown.py` caps the wait, so a steady stream of
merges cannot postpone every build.

## Considered Options

- A merge queue. Rejected: it builds the `merge_group` ref of each queued pull
  request and then builds the push to `main` again, multiplying builds instead
  of saving them.
- The wait timer of a deployment environment. It spends no runner time.
  Rejected: GitHub does not document whether concurrency cancels a job that
  waits on one.

## Consequences

- The workflow-level concurrency group is per run on `main`, so a run queued for
  the `ci` job never blocks the next run's cooldown.
