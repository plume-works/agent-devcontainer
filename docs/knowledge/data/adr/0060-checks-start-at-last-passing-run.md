---
type: adr
stage: accepted
description: On a push to main, the path filter and the pre-commit range start at the last passing run, not at the previous push.
---

# Push checks on main start at the last passing run

On `main`, a newer push or the cooldown cancels a run before it checks its
commits. For this reason, on a push to the base branch, the `paths-filter`
action and the `pre-commit` job start at the last passing run. They do not start
at the previous push.

## Considered Options

- Compare with the previous push only. Rejected: the changes of a cancelled or
  failed run never start the filtered jobs, and gitleaks never scans them.

## Consequences

- Each commit on `main` gets the filtered jobs, the hooks, and the gitleaks
  scan.
- When the search for the last passing run fails, the check uses the previous
  push and writes a warning.
- The searches are in `.github/actions/paths-filter/action.yml` and
  `scripts/pre-commit-ci-range.py::_widen_to_last_pass`.
