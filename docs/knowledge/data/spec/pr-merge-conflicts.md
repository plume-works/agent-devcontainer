---
type: spec
description: How pr-feedback-resolution and pr-merge detect a pull request's merge conflicts and resolve them — through update-branch against the PR's own base branch, or through gh stack for a stacked PR.
generated:
  by: claude-code/opus-5-5
  at: 2026-10-05T14:30:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/update-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/gh-stack/SKILL.md
---

# PR merge conflicts

## Purpose

Defines how the PR skills handle a pull request that conflicts with its base:
detected from GitHub's merge state, resolved before any feedback work — by
merging the PR's own base branch, or by a cascading `gh stack rebase` for a PR
in a GitHub stack — and pushed at once so CI runs on the resolved head.

## Requirements

### Requirement: Feedback resolution resolves merge conflicts first

The pr-feedback-resolution skill SHALL read the PR's `mergeable`,
`mergeStateStatus`, and `baseRefName` before any feedback edit. When `mergeable`
is `CONFLICTING` or `mergeStateStatus` is `DIRTY`, it SHALL resolve the conflict
before collecting feedback: a PR in a GitHub stack through `gh stack rebase` and
`gh stack push`, any other PR by merging its `baseRefName` through
`update-branch` and pushing the merge. When `mergeable` is `UNKNOWN`, it SHALL
re-poll before deciding. A PR that is only `BEHIND` its base SHALL NOT be
updated.

#### Scenario: Conflicted PR

- **WHEN** the PR's `mergeable` is `CONFLICTING` or `mergeStateStatus` is
  `DIRTY`, and the PR belongs to no GitHub stack
- **THEN** `update-branch` runs with `--base <baseRefName>` before any feedback
  edit
- **AND** the resolved merge is pushed before feedback is collected

#### Scenario: PR on another branch outside a stack

- **WHEN** a conflicted PR targets a branch other than `main` and belongs to no
  GitHub stack
- **THEN** that branch, not `main`, is merged into the PR branch

#### Scenario: Stacked PR

- **WHEN** a conflicted PR belongs to a GitHub stack
- **THEN** the conflict is resolved with `gh stack rebase` and the stack is
  pushed with `gh stack push`
- **AND** `update-branch` is not run

#### Scenario: Mergeability not yet computed

- **WHEN** `mergeable` is `UNKNOWN`
- **THEN** the merge state is re-polled in bounded waits before deciding

#### Scenario: Branch behind without conflicts

- **WHEN** `mergeStateStatus` is `BEHIND` and the PR has no conflicts
- **THEN** the branch is not updated and feedback collection proceeds

### Requirement: The merge monitoring loop routes conflicted PRs

The pr-merge monitoring loop SHALL read `mergeable` with the PR's merge state,
SHALL route a `CONFLICTING` or `DIRTY` PR to pr-feedback-resolution's
merge-conflict step and restart from its refresh, and SHALL re-poll an `UNKNOWN`
mergeability, both before waiting on checks.

#### Scenario: Conflicted PR during monitoring

- **WHEN** the refresh reports `mergeable: CONFLICTING` or
  `mergeStateStatus: DIRTY`
- **THEN** the loop follows the merge-conflict step instead of waiting on checks
- **AND** restarts at the refresh afterwards

#### Scenario: Mergeability not yet computed during monitoring

- **WHEN** the refresh reports `mergeable: UNKNOWN`
- **THEN** the loop restarts at the refresh after a bounded wait instead of
  waiting on checks

### Requirement: update-branch accepts a calling skill's remote and base

The update-branch skill SHALL accept `--remote` and `--base` values supplied by
the user or by a calling skill, and SHALL otherwise use `origin/main`.

#### Scenario: Calling skill supplies the base

- **WHEN** pr-feedback-resolution invokes update-branch with
  `--base <baseRefName>`
- **THEN** update-branch merges `origin/<baseRefName>`
