---
type: spec
description: How the git-new-branch skill starts a work branch at the fetched remote base, and how git-commit and pre-commit keep commits off the default branch.
generated:
  by: claude-code/opus-5.5
  at: 2026-09-29T12:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/git-new-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/git-new-branch/scripts/git-new-branch.sh
- resource: .agents/plugins/agentdev/bin/git-default-branch.sh
- resource: .agents/plugins/agentdev/skills/git-commit/SKILL.md
- resource: .agents/plugins/agentdev/skills/git-commit/scripts/git-commit.sh
- resource: .pre-commit-config.yaml
---

# git-new-branch

## Purpose

Defines how work gets onto its own branch: created at the freshly fetched remote
base, tracking its own upstream, with uncommitted changes and stray
default-branch commits carried onto it, and never committed on the default
branch.

## Requirements

### Requirement: A new branch starts at the fetched remote base with its own upstream

The git-new-branch skill SHALL fetch the remote, create the branch at
`<remote>/<base>` (falling back to the remote's default branch when `<base>`
does not exist), SHALL NOT set the base as the branch's upstream, and SHALL push
the branch immediately so it tracks `<remote>/<name>`.

#### Scenario: Branch created from main

- **WHEN** the user asks for branch `X` and `origin/main` exists
- **THEN** `X` points at the just-fetched `origin/main` commit
- **AND** `X` is pushed and tracks `origin/X`

#### Scenario: The remote has no main

- **WHEN** `origin/main` does not exist after fetching
- **THEN** the branch starts at the commit `refs/remotes/origin/HEAD` names

#### Scenario: The remote HEAD symref is unset

- **WHEN** `origin/main` does not exist and `refs/remotes/origin/HEAD` is unset
- **THEN** the branch starts at the default branch `gh repo view` reports for
  the remote's URL

#### Scenario: The push fails

- **WHEN** the push is rejected or authentication is unavailable
- **THEN** the local branch is kept, the skill reports `PUSH_FAILED`, and no
  API-based ref update is attempted

### Requirement: Existing branches are never reused

The git-new-branch skill SHALL refuse a name that exists as a local branch or on
the remote, and SHALL leave both untouched.

#### Scenario: The name exists only on the remote

- **WHEN** `origin/X` exists and local `X` does not
- **THEN** the skill reports `BRANCH_EXISTS` and creates nothing

### Requirement: Uncommitted changes survive branch creation

The git-new-branch skill SHALL carry uncommitted and untracked changes onto the
new branch, SHALL stash only after the user approves, and SHALL keep the stash
entry until any conflicts it produces are resolved.

#### Scenario: Changes carry over cleanly

- **WHEN** the working tree has changes to paths identical in HEAD and the base
- **THEN** the new branch is checked out with those changes intact

#### Scenario: Changes cannot be carried

- **WHEN** Git refuses to switch because local changes would be overwritten
- **THEN** the skill reports `CARRY_CONFLICT`, changes nothing, and asks the
  user before stashing

#### Scenario: The stash pops with conflicts

- **WHEN** the user approved stashing and the pop conflicts
- **THEN** the conflicts are resolved through the git-merge-resolve conflict
  workflow and the stash entry is dropped only afterwards

### Requirement: Worktree mode leaves the current checkout alone

In worktree mode the git-new-branch skill SHALL create the branch in a new
worktree named `<repo>-<branch>` under `/workspaces` when the main checkout
lives there, otherwise under the checkout's ignored `.worktrees/` directory, and
SHALL NOT change the current checkout.

#### Scenario: Repository outside /workspaces

- **WHEN** the main checkout is not directly under `/workspaces`
- **THEN** the worktree is created under `<checkout>/.worktrees/` and that
  directory is ignored by Git

### Requirement: Commits on the default branch move to the new branch

When the checkout is on `main` or `master` and holds commits the fetched base
lacks, the git-new-branch skill SHALL start the branch at `HEAD` and SHALL merge
the base into it through the update-branch skill. Outside worktree mode it SHALL
reset the local default branch to the fetched base once the new branch contains
the default branch's previous tip; in worktree mode it SHALL leave the default
branch unmoved.

#### Scenario: Local commits on main

- **WHEN** local `main` is two commits ahead of the fetched `origin/main`
- **THEN** the new branch starts at local `main`, the script reports
  `LOCAL_COMMITS=2`, and local `main` points at the fetched `origin/main`
- **AND** `origin/main` is then merged into the new branch through update-branch

#### Scenario: Local commits on main in worktree mode

- **WHEN** local `main` is ahead of `origin/main` and worktree mode is used
- **THEN** the worktree branch starts at local `main` and local `main` is not
  moved

### Requirement: The git-commit skill never commits on the default branch

The git-commit skill SHALL create commits only through its bundled script, which
SHALL refuse to run `git commit` on `main`, `master`, the remote's default
branch, or a detached `HEAD`, and SHALL direct the user to the git-new-branch
skill instead.

#### Scenario: Commit requested on main

- **WHEN** the user asks for a commit and the current branch is `main`
- **THEN** the script reports `PROTECTED_BRANCH`, no commit is created, and the
  user is pointed at git-new-branch

#### Scenario: A direct git commit on main in this repository

- **WHEN** someone runs `git commit` on `main` with the pre-commit hooks
  installed
- **THEN** the `no-commit-to-branch` hook fails and no commit is created

#### Scenario: The remote default branch has another name

- **WHEN** `refs/remotes/origin/HEAD` names `trunk` and the current branch is
  `trunk`
- **THEN** the script reports `PROTECTED_BRANCH` and no commit is created
