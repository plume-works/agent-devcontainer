# PR merge conflicts Specification

## Purpose

Defines how the PR skills handle a pull request that conflicts with its base:
detected from GitHub's merge state, resolved before any feedback work by merging
the PR's own base branch, and pushed at once so CI runs on the resolved head.

## Requirements

### Requirement: Feedback resolution resolves merge conflicts first

The pr-feedback-resolution skill SHALL read the PR's `mergeable`,
`mergeStateStatus`, and `baseRefName` before any feedback edit. When `mergeable`
is `CONFLICTING` or `mergeStateStatus` is `DIRTY`, it SHALL resolve the conflict
before collecting feedback by merging its `baseRefName` through `update-branch`
and pushing the merge. When `mergeable` is `UNKNOWN`, it SHALL re-poll before
deciding. A PR that is only `BEHIND` its base SHALL NOT be updated.

#### Scenario: Conflicted PR

- **WHEN** the PR's `mergeable` is `CONFLICTING` or `mergeStateStatus` is
  `DIRTY`
- **THEN** `update-branch` runs with `--base <baseRefName>` before any feedback
  edit
- **AND** the resolved merge is pushed before feedback is collected

#### Scenario: PR on another branch

- **WHEN** a conflicted PR targets a branch other than `main`
- **THEN** that branch, not `main`, is merged into the PR branch

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
