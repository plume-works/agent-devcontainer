---
type: spec
description: How the PR skills merge pull requests explicitly, merge a GitHub native stack through gh stack merge, limit force-pushes to stack branches, publish stack branches only through the push guard, and keep update-branch off stack branches.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-17T18:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md
- resource: .agents/plugins/agentdev/skills/update-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: AGENTS.md
- resource: .agents/plugins/agentdev/skills/gh-stack/SKILL.md
- resource: .agents/plugins/agentdev/skills/gh-stack/agent-code/stack-guard.sh
---

# Stacked PRs

## Purpose

Defines how the PR skills merge: every PR explicitly and never through
auto-merge, a PR in a GitHub native stack through `gh stack merge`, and branch
updates without force except `gh stack`'s lease-guarded updates of stack
branches. See [Stacked pull requests](../architecture/stacked-prs.md) for the
GitHub behavior these rules rest on.

## Requirements

### Requirement: pr-merge merges explicitly

The pr-merge skill SHALL NOT enable auto-merge. It SHALL disable an existing
auto-merge request when it starts and SHALL merge with a squash only after
conflicts, checks, AI review, and review feedback are resolved for the current
head SHA.

#### Scenario: Auto-merge already enabled

- **WHEN** pr-merge starts on a PR whose `autoMergeRequest` is non-null
- **THEN** it disables auto-merge before monitoring
- **AND** reports that it did so

#### Scenario: Requirements met

- **WHEN** every completion criterion holds for the current head SHA
- **THEN** pr-merge squash merges the PR explicitly and confirms `MERGED`

### Requirement: Stacked PRs merge through gh stack merge

A PR that belongs to a GitHub stack SHALL be merged with
`gh stack merge <pr> --yes --squash`, never with `gh pr merge`. pr-merge SHALL
merge only the lowest unmerged layer of a stack; pr-merge-stack SHALL bring
every unmerged layer through CI and review bottom-up and land them with one
`gh stack merge` of the top PR.

#### Scenario: Lowest unmerged layer

- **WHEN** pr-merge is asked to merge the lowest unmerged PR of a stack
- **THEN** it merges that PR with `gh stack merge <pr> --yes --squash`

#### Scenario: Higher layer

- **WHEN** pr-merge is asked to merge a stacked PR with unmerged PRs below it
- **THEN** it hands the stack to pr-merge-stack instead of merging

#### Scenario: Whole stack

- **WHEN** pr-merge-stack has every unmerged layer green for CI and review
- **THEN** it runs one `gh stack merge <top> --yes --squash`

### Requirement: Force-pushes are limited to stack branches

Agent skills SHALL NOT force-push, except that `gh stack rebase` and the
gh-stack skill's `stack-guard.sh publish` MAY update branches of a GitHub stack
with `--force-with-lease`. The repository-local `rerere.enabled` and
`remote.pushDefault` written by `gh stack` or the gh-stack skill's setup are the
only permitted git config changes.

#### Scenario: Branch outside a stack

- **WHEN** a skill must update a branch that belongs to no GitHub stack
- **THEN** it pushes without force

#### Scenario: Lower layer changed

- **WHEN** a commit lands on a lower layer of a stack
- **THEN** the layers above are updated with `gh stack rebase --upstack` and
  published with `stack-guard.sh publish`

### Requirement: update-branch refuses stack branches

The update-branch skill SHALL refuse a branch that belongs to a GitHub stack and
SHALL direct the caller to the gh-stack skill's post-merge refresh.

#### Scenario: Stack branch

- **WHEN** update-branch runs on a branch of a GitHub stack
- **THEN** it stops without merging and names the gh-stack skill's refresh

### Requirement: Stack pushes never drop remote-only commits

Agent skills SHALL update the remote branches of a GitHub stack only through
`stack-guard.sh publish`, never with a bare `gh stack push`, `gh stack submit`,
or `gh stack sync`. `stack-guard.sh begin` SHALL run before a skill rewrites a
stack layer. It SHALL fast-forward a layer that its remote is ahead of, and it
SHALL stop when a layer's remote holds a commit whose patch the local branch
lacks, or a merge commit it lacks, excluding the trunk. `publish` SHALL stop
when a layer's remote tip moved since `begin` to anything but its local tip,
SHALL report remote commits its push overwrote, and SHALL report a remote tip
that differs from its local tip after the push.

#### Scenario: Remote ahead

- **WHEN** `begin` runs and a layer's local tip is an ancestor of its remote tip
- **THEN** it fast-forwards the local layer and reports it

#### Scenario: Remote-only commit

- **WHEN** `begin` runs and a layer's remote holds a commit whose patch the
  local branch lacks
- **THEN** it stops, names the commit, and the skill asks the user how to
  incorporate it

#### Scenario: Remote rebased after a lower layer merged

- **WHEN** GitHub rebased a layer after a lower layer merged, and the remote
  holds no other commit
- **THEN** `begin` succeeds

#### Scenario: Remote moved during the edit

- **WHEN** a layer's remote tip changed between `begin` and `publish`
- **THEN** `publish` stops before pushing and names the layer

#### Scenario: Remote-only merge of the trunk

- **WHEN** a layer's remote holds a merge of the trunk the local branch lacks
- **THEN** `begin` stops and names the merge

#### Scenario: Push overwrote a concurrent push

- **WHEN** a layer's remote gained a commit after `publish` checked it and
  gh-stack's push replaced it
- **THEN** `publish` reports `REMOTE_OVERWRITTEN` and names the lost commits

#### Scenario: Push left a layer behind

- **WHEN** the gh-stack push exits `0` but a layer's remote tip differs from its
  local tip
- **THEN** `publish` reports the layer as not published
