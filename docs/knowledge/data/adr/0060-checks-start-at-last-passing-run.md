---
type: adr
stage: accepted
---

# Push checks on main start at the last passing run

On `main`, a newer push or the cooldown cancels a run before it checks its
commits. The cooldown is the time that a push to `main` waits in a job that CI
can cancel, so that many merges cause only one build. For this reason, on a push
to the base branch, the `paths-filter` action and the `pre-commit` job start at
the last passing run. They do not start at the previous push.

## Considered Options

- Compare with the previous push only. Rejected: the changes of a cancelled or
  failed run never start the filtered jobs, and gitleaks never scans them.
