---
type: task
created: 2026-10-31
stage: planned
priority: low
description: Decide from the pre-commit job's recorded step timings whether Primary checks should start the ci job in parallel with the pre-commit job instead of after it, and drop the needs gate if so.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T05:09:35Z
sources:
- resource: .github/workflows/primary-checks.yml
- resource: scripts/tests/test_pre_commit_ci_job.py
---

# Run Primary checks' ci job in parallel with the pre-commit job

Primary checks' `ci` job waits on the `pre-commit` job, which runs the hooks in
the digest-pinned `agentdev-devcontainer` image, through `needs:`.

The `pre-commit` job only checks and never pushes, so no formatter commit can
supersede the run while `ci` builds. What waiting still buys is image-build
runner time saved when lint fails; what it costs is the pre-commit job's full
duration added to every PR's wall clock.

## Work

- Read the pre-commit job's step timings (`uv sync`, `pre-commit install-hooks`,
  `pre-commit run`) from the jobs API across recent runs.
- Decide whether the wall-clock saving outweighs the runner time spent building
  images for PRs that fail lint, and record the decision either way.
- If parallel wins, drop the `needs:` gate from `ci` in
  `.github/workflows/primary-checks.yml` while the pre-commit job stays a
  required check.

## Dependencies

None open: the `pre-commit` job records each step's duration in the jobs API,
and `test_pre_commit_ci_job.py` asserts the `needs:` edge a change here would
drop.
