---
type: spec
description: How the git-new-branch skill starts a work branch at the fetched remote base, and how git-commit and pre-commit keep commits off the default branch.
sources:
- resource: .agents/plugins/agentdev/skills/git-new-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.py
- resource: .agents/plugins/agentdev/bin/git_default_branch.py
- resource: .agents/plugins/agentdev/skills/pr-open/agent-code/find-branch-pr.py
- resource: .agents/plugins/agentdev/skills/git-commit/SKILL.md
- resource: .agents/plugins/agentdev/skills/git-commit/agent-code/git-commit.py
- resource: .pre-commit-config.yaml
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: compose.opencode.yml
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
entry until any conflicts it produces are resolved. It SHALL pop only the stash
entry it created, found by its commit, never whatever is at `stash@{0}`, and
SHALL report that commit as `STASH_SHA` and its current position as `STASH_REF`
whenever it leaves the entry in the stash.

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
  workflow, every stashed path is confirmed recovered, and the stash entry is
  dropped only afterwards

#### Scenario: Nothing was stashed

- **WHEN** the user approved stashing and `git stash push` created no entry
- **THEN** no stash entry is popped, and a stash entry that existed before the
  run is left untouched

#### Scenario: The branch cannot be created after stashing

- **WHEN** the user approved stashing and `git switch` cannot create the branch
- **THEN** the skill pops its own entry back onto the unchanged checkout and
  reports `CREATE_FAILED`, naming the entry by `STASH_SHA` and `STASH_REF` if
  that pop fails

### Requirement: Worktree mode leaves the current checkout alone

In worktree mode the git-new-branch skill SHALL create the branch in a new
worktree named `<repo>-<branch>`, with any `/` in the branch kept as a directory
separator, under the checkout's ignored `.worktrees/` directory when
`AGENTDEV_RUNTIME_MODE` is `deploy`, otherwise under `/workspaces` when the main
checkout lives there and the account can write it, and under the checkout's
ignored `.worktrees/` directory when not, and SHALL NOT change the current
checkout.

#### Scenario: Repository outside /workspaces

- **WHEN** the main checkout is not directly under `/workspaces`
- **THEN** the worktree is created under `<checkout>/.worktrees/` and that
  directory is ignored by Git

#### Scenario: Deploy runtime

- **WHEN** `AGENTDEV_RUNTIME_MODE` is `deploy`, whether or not the main checkout
  is directly under `/workspaces`
- **THEN** the worktree is created under `<checkout>/.worktrees/` and that
  directory is ignored by Git

#### Scenario: An account that cannot write /workspaces

- **WHEN** the main checkout is directly under `/workspaces` and the account
  cannot write `/workspaces`
- **THEN** the worktree is created under `<checkout>/.worktrees/` and that
  directory is ignored by Git

#### Scenario: Branch names that differ only by `/` and `-`

- **WHEN** worktrees for `feature/foo` and `feature-foo` are created under the
  same parent
- **THEN** each gets its own directory

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
skill instead. When the remote exists but its default branch cannot be
determined, it SHALL refuse as well.

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

#### Scenario: The remote default branch is unknown

- **WHEN** `origin` exists, `refs/remotes/origin/HEAD` is unset, `gh` cannot
  report the default branch, and the current branch is not `main` or `master`
- **THEN** the script reports `DEFAULT_UNKNOWN` and no commit is created

## Rationale

### The branch tracks its own upstream from creation

The branch is created with `--no-track` and pushed at once. A branch made with
`git switch -c X origin/main` tracks the base, so `git pull` pulls the base and
`pr-open`'s `find-branch-pr.py` refuses it as `PROTECTED_BRANCH`, since its
upstream is the default branch.

Rejected:

- **Pushing at the first commit.** The upstream stays unset in between, and
  `pr-open` has to finish the setup.

### Deploy worktrees live inside the checkout

The deploy image mounts only `/workspaces/project`, as a named volume or a host
bind. `/workspaces` itself is created root-owned by the image's `WORKDIR` and
lives in the container layer, so a worktree there would be unwritable for the
agent user and lost when the container is recreated. Deploy mode therefore puts
worktrees in the checkout's ignored `.worktrees/`.
