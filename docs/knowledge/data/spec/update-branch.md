---
type: spec
description: How the update-branch skill brings in the branch's own upstream before merging the base, and how a conflicted merge stops the run and a rerun continues.
sources:
- resource: .agents/plugins/agentdev/skills/update-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/update-branch/agent-code/update-branch.py
- resource: .agents/plugins/agentdev/tests/test_update_branch.py
- resource: .agents/plugins/agentdev/skills/git-merge-resolve/agent-code/git-merge-resolve.py
---

# update-branch

## Purpose

Defines how the update-branch skill brings a feature branch up to date: the
commits its own upstream gained on the remote come in first, then the remote
base branch is merged, with every merge stopping on conflicts and a rerun
continuing from the merge that stopped.

## Requirements

### Requirement: update-branch brings in the branch's upstream before the base

The update-branch skill SHALL bring the commits of the current branch's
configured upstream into the branch before it merges the base ref — by
fast-forward when the branch is only behind the upstream, by a merge commit when
they diverged — and SHALL NOT rebase, reset, or force-push to do so. It SHALL
decide whether the branch is already up to date only after that sync. When the
upstream branch no longer exists on its remote, it SHALL warn, merge the base,
and let its push recreate the remote branch. The upstream SHALL count as gone
only when
`git ls-remote --exit-code --heads <upstream-remote> <upstream-branch>` exits
`2`; any other failure of that command SHALL be `FETCH_FAILED`. An upstream on
the local repository (`branch.<name>.remote` is `.`) SHALL be synced like any
other, with no fetch and no existence check.

#### Scenario: The branch is behind its upstream

- **WHEN** `origin/X` holds commits the local branch `X` lacks and `X` has no
  commits `origin/X` lacks
- **THEN** `X` is fast-forwarded to `origin/X` before `origin/main` is merged
- **AND** `UPSTREAM_ACTION` is `fast-forward`

#### Scenario: The branch and its upstream diverged

- **WHEN** `X` and `origin/X` each hold commits the other lacks
- **THEN** `origin/X` is merged into `X` with a merge commit before
  `origin/main` is merged
- **AND** `UPSTREAM_ACTION` is `merge`

#### Scenario: The upstream already contains the base

- **WHEN** `X` is behind `origin/X` and `origin/X` already contains
  `origin/main`
- **THEN** `X` is fast-forwarded and no merge commit is created
- **AND** the skill reports `ALREADY_UP_TO_DATE`

#### Scenario: The branch has no upstream

- **WHEN** `X` has no configured upstream
- **THEN** the base is merged as before and `UPSTREAM_ACTION` is `untracked`

#### Scenario: The upstream is the base ref

- **WHEN** `X` tracks `origin/main` and `origin/main` is the base ref
- **THEN** no separate upstream sync runs, the base is merged once, and
  `UPSTREAM_ACTION` is `base`

#### Scenario: The upstream branch is gone

- **WHEN** `X` tracks `origin/X` and `origin/X` no longer exists on the remote
- **THEN** a warning is printed, the base is merged, and `UPSTREAM_ACTION` is
  `gone`
- **AND** the push that follows recreates `origin/X`

#### Scenario: The upstream lives on another remote

- **WHEN** `X` tracks `fork/X` and the base remote is `origin`
- **THEN** `fork` is fetched too and `fork/X` is brought in before `origin/main`
  is merged
- **AND** a failed fetch of `fork` is reported as `FETCH_FAILED`

#### Scenario: The upstream query fails

- **WHEN** `git ls-remote --exit-code --heads` for the upstream exits with a
  status other than `0` or `2`
- **THEN** the skill reports `FETCH_FAILED` and merges nothing
