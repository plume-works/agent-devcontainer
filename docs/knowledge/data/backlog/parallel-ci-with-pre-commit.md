---
type: task
created: 2026-10-31
stage: planned
priority: low
description: Decide from the pre-commit job's recorded step timings whether Primary checks should start the ci job in parallel with the pre-commit job instead of after it, and drop the needs gate if so.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T12:00:00Z
sources:
- resource: .github/workflows/primary-checks.yml
- resource: .github/workflows/reformat.yml
---

# Run Primary checks' ci job in parallel with the pre-commit job

Once Super-Linter and `reformat.yml` are replaced by a CI pre-commit job running
in the digest-pinned `agentdev-devcontainer` image, `ci` keeps waiting on that
job through `needs:`, matching the current `reformat → ci` order.

The original reason for the serial order — a formatter commit pushed to the head
supersedes the run — is gone once the CI job only checks and never pushes. What
waiting still buys is image-build runner time saved when lint fails; what it
costs is the pre-commit job's full duration added to every PR's wall clock.

## Work

- Read the pre-commit job's step timings (`uv sync`, `pre-commit install-hooks`,
  `pre-commit run`) from the jobs API across recent runs.
- Decide whether the wall-clock saving outweighs the runner time spent building
  images for PRs that fail lint, and record the decision either way.
- If parallel wins, drop the `needs:` gate from `ci` in
  `.github/workflows/primary-checks.yml` while the pre-commit job stays a
  required check.

## Dependencies

Blocked on the plan that removes Super-Linter and introduces the CI pre-commit
job: it supplies the job and the timing data this decision needs.
