---
type: spec
description: How the iwe-branch-name skill names a plan's impl and ship work branches, counts the iterations already used, and reads plan state in the checkout.
sources:
- resource: .agents/plugins/agentdev/skills/iwe-branch-name/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py
- resource: .agents/plugins/agentdev/bin/git_default_branch.py
---

# iwe-branch-name

## Purpose

Defines the name of every work branch a plan uses, how the next iteration is
counted so a merged and deleted branch is never reused, and how a plan's state
is read from the checkout to pick the phase.

## Requirements

### Requirement: Plan work branches carry phase, slug, and iteration

The iwe-branch-name skill SHALL name a plan's work branch
`iwe/<slug>/iter-<N>-<phase>`, where `slug` is the plan key's file name without
its `YYYYMMDD-` prefix, `N` is a positive integer, and `phase` is `plan`,
`impl`, or `ship`, and SHALL always include the `iwe/` prefix and the iteration
suffix.

#### Scenario: First implementation branch

- **WHEN** no branch or pull request named `iwe/foo/iter-<N>-<phase>` exists for
  plan `data/plans/20261020-foo`
- **THEN** the next `impl` name is `iwe/foo/iter-1-impl`

#### Scenario: A name off the shape is not parsed

- **WHEN** `parse` receives `foo`, `impl/foo/iter-1`, `iwe/foo/iter-1`, or
  `iwe/foo/iter-0-impl`
- **THEN** it reports `NOT_A_WORK_BRANCH` and no phase, slug, or iteration

### Requirement: The next iteration follows every iteration already used

The skill SHALL compute the next `N` for a slug as one more than the highest `N`
of any phase among local branches, the remote's branches, and the pull requests
in any state of the repository the remote's URL names, counting only names that
match the shape exactly, and SHALL fail with `GH_UNAVAILABLE` rather than answer
when those pull requests cannot be read.

#### Scenario: A merged iteration's branch was deleted

- **WHEN** `iwe/foo/iter-2-impl` survives only as a merged pull request's head
  and `iwe/foo/iter-1-impl` exists locally
- **THEN** the next `impl` name is `iwe/foo/iter-3-impl`

#### Scenario: Names from before the iwe/ shape are not counted

- **WHEN** only `impl/foo/iter-4` exists for plan `foo`
- **THEN** the next `impl` name is `iwe/foo/iter-1-impl`

#### Scenario: gh cannot answer

- **WHEN** `gh` is missing or unauthenticated, or the remote's URL names no
  repository `gh` can read
- **THEN** `next` reports `GH_UNAVAILABLE` and no name

#### Scenario: Pull requests come from the remote's repository

- **WHEN** `next` runs with `--remote upstream`
- **THEN** it reads pull requests of the repository `upstream`'s URL names, not
  of `gh`'s default repository

### Requirement: Plan state is read in the checkout

The skill SHALL read the plan from the working tree, never from another branch,
looking under `data/plans/` and under every `data/archive/<release>/plans/`,
reporting `missing`, `cancelled`, `done`, `complete` when the plan has no
`stage`, has at least one task checkbox under `## Implementation Steps` or
`## Tasks`, and every such checkbox is ticked, or `incomplete` otherwise, and
SHALL refuse a slug that matches more than one plan with `AMBIGUOUS_PLAN`.

#### Scenario: Working-tree edits count

- **WHEN** a plan's last checkbox is ticked only in the working tree
- **THEN** `plan-state` reports `complete`

#### Scenario: The remote default branch does not count

- **WHEN** a plan is finished only on the remote default branch
- **THEN** `plan-state` reports the plan as the working tree holds it

#### Scenario: A plan with no task checkboxes is not complete

- **WHEN** a plan has no `stage` and no task checkbox
- **THEN** `plan-state` reports `incomplete`

#### Scenario: The older task heading counts

- **WHEN** a plan without `stage` lists every task ticked under `## Tasks`
- **THEN** `plan-state` reports `complete`

#### Scenario: An archived plan is a dependency

- **WHEN** a plan exists only under `data/archive/2.1.0/plans/` at `stage: done`
- **THEN** `plan-state` reports `done`

#### Scenario: Two plans share a slug

- **WHEN** `data/plans/20261001-foo` and `data/archive/2.1.0/plans/20261020-foo`
  both exist in the working tree
- **THEN** a lookup by slug `foo` reports `AMBIGUOUS_PLAN`

### Requirement: The next name follows the plan's state

Without an explicit phase, `next` SHALL name the remote default branch for a
`done`, `cancelled`, or `missing` plan, the next `ship` iteration for a
`complete` plan, and the next `impl` iteration for an `incomplete` plan; with
`--phase`, it SHALL name the next iteration of that phase without reading the
plan. The skill SHALL NOT create, switch, or delete any branch.

#### Scenario: A complete plan moves to shipping

- **WHEN** plan `foo` is `complete` and `iwe/foo/iter-1-ship` was used before
- **THEN** `next foo` reports `NEXT=iwe/foo/iter-2-ship`

#### Scenario: A shipped plan returns to the default branch

- **WHEN** plan `foo` is `done`
- **THEN** `next foo` reports `NEXT_KIND=default` and the default branch's name

## Rationale

### One iteration counter per plan, under one prefix

`N` is the plan's Nth work branch whatever its phase, so the names alone order a
plan's pull requests. Two checkouts racing may both take one `N` in different
phases; that is accepted, because the maximum still orders every later name
after both.

The fixed `iwe/` prefix keeps every plan branch in one ref namespace, so a
branch named after a bare slug never blocks a work branch; only a ref named
exactly `iwe` or `iwe/<slug>` could, and the tooling makes neither. Every name
ends in `iter-<N>-<phase>`, so no work branch is a path prefix of another.

Names in the earlier `impl/<slug>/iter-<N>` and `ship/<slug>/iter-<N>` shape are
not work branches and are never counted, renamed, or migrated: the maintainer
chose a clean break over carrying two shapes, so a plan whose only branches
carry the earlier shape starts at `iter-1`.

Rejected:

- **A counter per phase.** It could not say whether `impl/foo/iter-3` came
  before or after `ship/foo/iter-1`.
- **`<slug>/iter-<N>-<phase>` without a prefix.** A branch named after the bare
  slug blocks every work branch of that plan.
- **Phase first with a shared counter, such as `impl/foo/iter-3`.** The phase
  prefix reads as a per-phase count.
- **A bare name for the first iteration.** Git cannot hold a ref beside another
  it would nest under, so a bare `iwe/<slug>` would block every later
  `iwe/<slug>/iter-<N>-<phase>`.
- **Other suffix words.** `iteration-<N>` is long, `t<N>` reads as plan Task N,
  `take<N>` implies the previous branch was discarded, `v<N>` reads as a release
  version, a bare `<N>` or a flat `<slug>-<N>` is ambiguous beside slugs ending
  in digits, and `pr<N>` or `#<N>` reads as a pull request number, `#` also
  starting a shell comment.

### Merged and closed pull requests count because merged branches are deleted

This repository squash-merges and deletes the head branch on merge, so after a
merge nothing in the remote's branch list records which iteration comes next;
the skill exists to count it. `next` fails with `GH_UNAVAILABLE` rather than
return a lower bound, because a merged pull request may already hold that number
and a reused name mixes pull-request history across iterations. The lookup
relies on two `gh` facts: GitHub's `head:` pull-request search matches by
prefix, so results are filtered to names matching the shape exactly, and
`gh --repo` accepts a remote's HTTPS, SSH, or scp-style URL as is, so the URL is
passed unparsed and branches and pull requests come from one repository.

Rejected:

- **A lower bound from branches alone when `gh` fails.** It can reuse a merged
  iteration's name.
- **Deriving `N` from the current branch.** It has no answer on the default
  branch and misses iterations made in other checkouts.

### The skill names branches and creates none

Branch creation stays in one place, `/agentdev:git-new-branch`, so the skill
only prints names.

Rejected:

- **Creating the branch in the skill.** It would duplicate
  `/agentdev:git-new-branch`.
