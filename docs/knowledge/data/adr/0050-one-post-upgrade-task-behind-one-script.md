---
type: adr
stage: accepted
---

# One post-upgrade task behind one script

Renovate stops updating a branch that carries a commit it did not author. As a
result, the files that a version update changes in turn (checksums, lock files,
and pre-commit fixes) must be in the commit of Renovate.
`.github/renovate.json#postUpgradeTasks` names one script,
`scripts/renovate-post-upgrade.py`, in `branch` mode. `postUpgradeTasks` is an
object that a later matching `packageRule` replaces rather than extends, so one
script behind one top-level task has no override ordering to get wrong.

## Considered Options

- One `postUpgradeTasks` for each type of pin. Rejected: a checksum rule would
  silently replace the pre-commit step.
- Skip the lint gate on Renovate pull requests. It keeps Renovate's branches
  free of foreign commits just as well. Rejected: a gap in the post-upgrade task
  would merge unnoticed.

## Consequences

- A new pin with a checksum needs its file in
  `scripts/refresh-pin-checksums.py@PIN_FILES`.
- Renovate keeps the output of the task only for paths that `fileFilters`
  matches. Each path that a Renovate manager edits must match it.
- The script runs pre-commit through `uv run`, never the image's unpinned apt
  copy, so the pass formats with the versions that the update pins: `uv run`
  syncs the environment to the bumped `uv.lock` before pre-commit starts.
- CI never pushes a fix to a Renovate branch. Its pre-commit job fails the pull
  request when the post-upgrade task missed a change.
- The task runs code at just-bumped versions as the same user as Renovate, so
  `.github/workflows/renovate.yml` names each permission of the App token
  instead of inheriting the installation's. A permission that the App gets later
  does not go into this token.
