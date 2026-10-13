---
type: spec
description: How the update-branch skill brings in the branch's own upstream before merging the base, and how a conflicted merge stops the run and a rerun continues.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-12T22:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/update-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/update-branch/agent-code/update-branch.sh
- resource: .agents/plugins/agentdev/tests/test_update_branch.py
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
decide whether the branch is already up to date only after that sync.

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

#### Scenario: The upstream lives on another remote

- **WHEN** `X` tracks `fork/X` and the base remote is `origin`
- **THEN** `fork` is fetched too and `fork/X` is brought in before `origin/main`
  is merged
- **AND** a failed fetch of `fork` is reported as `FETCH_FAILED`

### Requirement: Each conflicted merge stops the run and a rerun continues

The update-branch skill SHALL stop at the first merge that conflicts, report
`MERGE_CONFLICTS` with `SOURCE` naming the ref being merged, and leave any later
merge undone. A rerun after the resolution is committed SHALL treat the resolved
merge as done and continue with the next one.

#### Scenario: The upstream merge conflicts

- **WHEN** merging `origin/X` into `X` conflicts
- **THEN** the skill reports `MERGE_CONFLICTS` with `SOURCE=origin/X`
- **AND** `origin/main` is not merged in that run

#### Scenario: Rerun after resolving the upstream merge

- **WHEN** the upstream conflict is resolved and committed and the skill runs
  again
- **THEN** `UPSTREAM_ACTION` is `none` and `origin/main` is merged

#### Scenario: The base merge conflicts

- **WHEN** the upstream sync succeeds and merging `origin/main` conflicts
- **THEN** the skill reports `MERGE_CONFLICTS` with `SOURCE=origin/main`
