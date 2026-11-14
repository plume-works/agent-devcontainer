---
type: adr
stage: accepted
description: Renovate runs one top-level post-upgrade task, scripts/renovate-post-upgrade.py, which commits the derived files of a version update in the update commit of Renovate.
---

# One post-upgrade task behind one script

Renovate stops its updates to a branch that has a commit from a different
author. As a result, the derived files of a version update must be in the commit
of Renovate. `.github/renovate.json#postUpgradeTasks` names one script,
`scripts/renovate-post-upgrade.py`, in `branch` mode. A `packageRule` that sets
`postUpgradeTasks` replaces the top-level object and does not add to it.

## Considered Options

- One `postUpgradeTasks` for each type of pin. Rejected: a checksum rule would
  replace the pre-commit step, and nothing would show it.
- No lint gate on Renovate pull requests. Rejected: a gap in the post-upgrade
  task would then merge and nothing would show it.

## Consequences

- The script runs pre-commit through `uv run --frozen`. As a result, the hooks
  run at the versions that the update pins, not at the apt copy in the image.
- When the `dev_tools` pins change, the script runs `iwe normalize` with the new
  `iwe`, because the image still has the old version.
- Renovate keeps the output of the task only for paths that `fileFilters`
  matches. Each path that a Renovate manager edits must match it.
- CI never pushes a fix to a Renovate branch. Its pre-commit job fails the pull
  request when the post-upgrade task missed a change.
- The task runs code at new versions with the token of Renovate, so
  `.github/workflows/renovate.yml` names each permission of the App token.
