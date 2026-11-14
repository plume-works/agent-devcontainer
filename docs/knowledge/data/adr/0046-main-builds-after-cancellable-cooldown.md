---
type: adr
stage: accepted
description: A push to main waits a cooldown in a job that a newer push cancels, so a burst of merges builds once, and a time limit makes sure that a steady flow of merges cannot delay each build.
---

# Pushes to main build after a cooldown that a newer push cancels

Each Primary checks run on `main` is a clean multi-arch build, and these runs
wait in a queue after their build starts. The `cooldown` job in
`.github/workflows/primary-checks.yml` has its own cancel-in-progress group, so
a newer push cancels a run before its build starts. `scripts/ci-cooldown.py`
limits the wait, so a steady flow of merges cannot delay every build.

## Considered Options

- A merge queue. Rejected: it builds the `merge_group` ref of each queued pull
  request and then builds the push to `main` again.
- The wait timer of a deployment environment. Rejected: GitHub does not say if
  concurrency cancels a job that waits on one.

## Consequences

- The workflow-level concurrency group is one for each run on `main`. As a
  result, a run that waits for the `ci` job never blocks the cooldown of the
  next run.
