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

- The script gets the changed files from `git diff HEAD` in the clone of
  Renovate. It calculates the SHA-256 of each pin in a changed pin file again.
  This step fails when it cannot download a file, or when a pin with no version
  change gets a different checksum. As a result, no pull request has a new
  version with an old checksum.
- `scripts/refresh-pin-checksums.py` makes each download URL from the templates
  of the file that installs the tool, so it downloads the same file. A new pin
  with a checksum needs its file in
  `scripts/refresh-pin-checksums.py::PIN_FILES`.
- The pre-commit pass on the changed files can change files on its first run.
  Then the script runs it again, and a hook that fails again fails the branch.
  The pass skips `no-commit-to-branch`, because the clone of Renovate is on the
  base.
- The script runs pre-commit through `uv run --frozen`. As a result, the hooks
  run at the versions that the update pins, not at the apt copy in the image.
- When the `dev_tools` pins change, the script runs `iwe normalize` with the new
  `iwe`, because the image still has the old version.
- Renovate keeps the output of the task only for paths that `fileFilters`
  matches. Each path that a Renovate manager edits must match it.
- CI never pushes a fix to a Renovate branch. Its pre-commit job fails the pull
  request when the post-upgrade task missed a change. When a pull request
  changes a file in `scripts/pre-commit-ci-range.py::TOOL_VERSION_OWNERS`, the
  job runs each hook on each file.
- The macOS bootstrap pins the same release tools as `dev_tools`, and one
  Renovate group holds both files. As a result, one pull request changes the
  Linux and macOS pins of a tool together.
- The task runs code at new versions with the token of Renovate, so
  `.github/workflows/renovate.yml` names each permission of the App token: write
  on contents, pull requests, issues, workflows, checks, and statuses, and read
  on administration and vulnerability alerts. A permission that the App gets
  later does not go into this token.
- `RENOVATE_ALLOWED_COMMANDS` in `.github/workflows/renovate.yml` permits only
  the post-upgrade script, through an anchored pattern.
