---
type: spec
description: How the iwe-branch-name skill names a plan's impl and ship work branches, counts the iterations already used, and reads plan state at the remote default branch.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-25T00:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-branch-name/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py
- resource: .agents/plugins/agentdev/bin/git-default-branch.sh
---

# iwe-branch-name

## Purpose

Defines the name of every work branch a plan uses, how the next iteration is
counted so a merged and deleted branch is never reused, and how a plan's state
is read from the remote default branch to pick the phase.

## Requirements

### Requirement: Plan work branches carry phase, slug, and iteration

The iwe-branch-name skill SHALL name a plan's work branch
`<phase>/<slug>/iter-<N>`, where `phase` is `impl` or `ship`, `slug` is the plan
key's file name without its `YYYYMMDD-` prefix, and `N` is a positive integer,
and SHALL always include the iteration suffix.

#### Scenario: First implementation branch

- **WHEN** no branch or pull request of phase `impl` exists for plan
  `data/plans/20261020-foo`
- **THEN** the next `impl` name is `impl/foo/iter-1`

#### Scenario: A name off the shape is not parsed

- **WHEN** `parse` receives `foo`, `impl/foo`, or `impl/foo/iter-0`
- **THEN** it reports `NOT_A_WORK_BRANCH` and no phase, slug, or iteration

### Requirement: The next iteration follows every iteration already used

The skill SHALL compute the next `N` for a phase and slug as one more than the
highest `N` among local branches, the remote's branches, and the pull requests
in any state of the repository the remote's URL names, counting only names that
match the shape exactly, and SHALL fail with `GH_UNAVAILABLE` rather than answer
when those pull requests cannot be read.

#### Scenario: A merged iteration's branch was deleted

- **WHEN** `impl/foo/iter-2` survives only as a merged pull request's head and
  `impl/foo/iter-1` exists locally
- **THEN** the next `impl` name is `impl/foo/iter-3`

#### Scenario: gh cannot answer

- **WHEN** `gh` is missing or unauthenticated, or the remote's URL names no
  repository `gh` can read
- **THEN** `next` reports `GH_UNAVAILABLE` and no name

#### Scenario: Pull requests come from the remote's repository

- **WHEN** `next` runs with `--remote upstream`
- **THEN** it reads pull requests of the repository `upstream`'s URL names, not
  of `gh`'s default repository

### Requirement: Plan state is read at the remote default branch

The skill SHALL fetch the remote's default branch and read the plan there,
reporting `missing`, `cancelled`, `done`, `complete` when the plan has no
`stage`, has at least one task checkbox under `## Implementation Steps` or
`## Tasks`, and every such checkbox is ticked, or `incomplete` otherwise, and
SHALL refuse a slug that matches more than one plan with `AMBIGUOUS_PLAN`.

#### Scenario: Local edits do not count

- **WHEN** a plan's last checkbox is ticked only in the working tree
- **THEN** `plan-state` reports `incomplete`

#### Scenario: A plan with no task checkboxes is not complete

- **WHEN** a plan has no `stage` and no task checkbox
- **THEN** `plan-state` reports `incomplete`

#### Scenario: The older task heading counts

- **WHEN** a plan without `stage` lists every task ticked under `## Tasks`
- **THEN** `plan-state` reports `complete`

#### Scenario: Two plans share a slug

- **WHEN** `data/plans/20261001-foo` and `data/plans/20261020-foo` both exist at
  the remote default branch
- **THEN** a lookup by slug `foo` reports `AMBIGUOUS_PLAN`

### Requirement: The next name follows the plan's state

Without an explicit phase, `next` SHALL name the remote default branch for a
`done`, `cancelled`, or `missing` plan, the next `ship` iteration for a
`complete` plan, and the next `impl` iteration for an `incomplete` plan; with
`--phase`, it SHALL name the next iteration of that phase without reading the
plan. The skill SHALL NOT create, switch, or delete any branch.

#### Scenario: A complete plan moves to shipping

- **WHEN** plan `foo` is `complete` and `ship/foo/iter-1` was used before
- **THEN** `next foo` reports `NEXT=ship/foo/iter-2`

#### Scenario: A shipped plan returns to the default branch

- **WHEN** plan `foo` is `done`
- **THEN** `next foo` reports `NEXT_KIND=default` and the default branch's name
