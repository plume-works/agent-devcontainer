---
type: plan
created: 2026-09-28
description: Add the git-new-branch skill, which creates a work branch at the freshly fetched remote base with its real upstream, and route every "get onto a feature branch" instruction in the catalog through it.
generated:
  by: claude-code/opus-5.5
  at: 2026-09-28T19:23:21Z
sources:
- resource: .agents/plugins/agentdev/skills/update-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/skills/skill-scripts/SKILL.md
---

# git-new-branch skill

## Context

No catalog skill creates a branch. The skills that need one only tell the agent
to make it: `pr-open`'s `PROTECTED_BRANCH` handling prints
`git checkout -b feature/your-feature-name`, which branches from the checked-out
HEAD, not from the freshly fetched remote base, and `update-branch`'s
`PROTECTED_BRANCH` row says "switch to a feature branch" without saying how.
`iwe-implement` starts executing a plan on whatever branch is current.

A branch created with `git switch -c X origin/main` also tracks `origin/main`,
which `pr-open`'s `find-branch-pr.sh` rejects as `PROTECTED_BRANCH` ("the
upstream it tracks is `main`"), so the ad-hoc instruction produces a branch the
next skill refuses.

## Approach

A new `git-new-branch` skill — the start-of-work sibling of `update-branch` —
owns branch creation through one bundled script,
`git-new-branch.sh <name> [--remote origin] [--base main] [--worktree] [--worktree-root <dir>] [--stash]`,
following the `skill-scripts` result contract:

1. Preflight: inside a repository, and `git check-ref-format --branch <name>`
   accepts the name.
2. `git fetch <remote>`.
3. Resolve the base: `<remote>/<base>` (default `main`); when that ref does not
   exist, fall back to the remote's default branch through
   `refs/remotes/<remote>/HEAD`.
4. Refuse when local `<name>` or `<remote>/<name>` already exists — an existing
   branch is never reset or reused.
5. Create the branch with `--no-track` at the resolved base, switching the
   current checkout. Uncommitted changes carry over when Git can carry them.
6. `git push -u <remote> <name>` immediately, so the branch tracks
   `<remote>/<name>` from the start and never the base.

Uncommitted changes that Git refuses to carry (the paths differ between HEAD and
the base) yield `CARRY_CONFLICT` without touching anything. The SKILL.md then
asks the user; on approval it reruns with `--stash`, which stashes (including
untracked files), creates and pushes the branch, and pops the stash onto it. A
conflicted pop is resolved with `git-merge-resolve`'s conflict workflow; the
stash entry is dropped only after resolution.

`--worktree` leaves the current checkout alone and adds a worktree for the new
branch instead. The worktree directory name is `<repo>-<branch>` with `/` in the
branch replaced by `-`, where `<repo>` is the main checkout's directory name.
Its parent is `/workspaces` when the main checkout lives directly under
`/workspaces`, otherwise `<main checkout>/.worktrees`; `--worktree-root`
overrides both. Task 3 adds `.worktrees/` to this repository's `.gitignore`, and
the script adds it to `.git/info/exclude` when a consuming repository does not
already ignore it.

The SKILL.md suggests a name from context when the user gives none: a plan key
`data/plans/<date>-<slug>` → `<slug>`; a GitHub issue → `<number>-<slug>`.

Rejected: tracking the base (`git switch -c X origin/main`) — it makes
`git pull` pull the base and trips `pr-open`'s tracked-upstream check; deferring
the push to the first commit — the upstream would stay unset in between and
`pr-open` would have to finish the setup; silently stashing on conflict —
changes are never stashed without user approval (`update-branch`'s
`PREFLIGHT_ERROR` rule).

## Implementation Steps

### Task 1: Bundled script and its tests

**Files:** Create:
`.agents/plugins/agentdev/skills/git-new-branch/scripts/git-new-branch.sh`,
`.agents/plugins/agentdev/skills/git-new-branch/scripts/__common.sh`,
`.agents/plugins/agentdev/tests/test_git_new_branch.py`

- [x] Script follows the `skill-scripts` contract (shared `bin/result-codes.sh`,
  `RESULT=` last on stdout, paired `--help` table) with results `SUCCESS 0`,
  `BRANCH_EXISTS 3`, `CARRY_CONFLICT 4`, `PUSH_FAILED 5`, `FETCH_FAILED 6`,
  `STASH_CONFLICTS 7`, `PREFLIGHT_ERROR 2`, `SCRIPT_FAILURE 1`, and output keys
  `BRANCH`, `BASE`, `BASE_SHA`, plus `WORKTREE` in worktree mode and `STASH_REF`
  when a stash is left to resolve
  - **Evidence:** commit "feat(git-new-branch): add the branch-creation script
    and its tests"; `git-new-branch.sh --help` prints the paired results table;
    `shellcheck -x` clean on both scripts.
- [x] Tests against a local bare-repository remote cover: the created branch
  sits at the fetched base SHA and tracks `<remote>/<name>`; fallback to
  `<remote>/HEAD` when `<base>` is absent; `BRANCH_EXISTS` for a local and for a
  remote-only name; non-conflicting uncommitted and untracked changes carried
  over; `CARRY_CONFLICT` leaving the checkout and changes untouched; `--stash`
  success and `STASH_CONFLICTS` with the stash entry kept; worktree placement
  under `--worktree-root` and under `.worktrees/` with the exclude entry;
  `FETCH_FAILED`; `PUSH_FAILED` from a rejecting remote hook with the local
  branch kept; `PREFLIGHT_ERROR` for an invalid name
  - **Evidence:** commit "feat(git-new-branch): add the branch-creation script
    and its tests";
    `uv run pytest .agents/plugins/agentdev/tests/test_git_new_branch.py` 13
    passed.

### Task 2: Skill definition

**Files:** Create: `.agents/plugins/agentdev/skills/git-new-branch/SKILL.md`

- [ ] SKILL.md with discovery description, name suggestion rules, the
  `RESULT`-keyed decision table, the `CARRY_CONFLICT` question (stash and retry
  with `--stash`, or cancel), the `STASH_CONFLICTS` route through
  `git-merge-resolve`'s "Resolve Conflicts" workflow followed by
  `git stash drop <STASH_REF>` instead of a merge commit, and the safety rules
  (never reset an existing branch, never force-push, never update refs through
  an API)

### Task 3: Catalog listing and ignore rule

**Files:** Modify: `.agents/plugins/agentdev/README.md`, `.gitignore`

- [ ] `/agentdev:git-new-branch` row in the "Pull requests and git" table
- [ ] `.worktrees/` in `.gitignore` next to the `.tmp/` scratch entry

### Task 4: Route pr-open through git-new-branch

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-open/SKILL.md`

- [ ] The `PROTECTED_BRANCH` row and the "Not on a feature branch" message
  direct the agent to `/agentdev:git-new-branch` instead of
  `git checkout -b feature/your-feature-name`

### Task 5: Route update-branch through git-new-branch

**Files:** Modify: `.agents/plugins/agentdev/skills/update-branch/SKILL.md`

- [ ] The `PROTECTED_BRANCH` row and the "Current branch is default"
  troubleshooting row direct the agent to `/agentdev:git-new-branch`, only with
  user authorization

### Task 6: Point git-merge-resolve at its new caller

**Files:** Modify: `.agents/plugins/agentdev/skills/git-merge-resolve/SKILL.md`

- [ ] "When to Use This Skill" names resolving the conflicts a
  `git-new-branch --stash` pop leaves, completed by dropping the stash rather
  than committing a merge

### Task 7: Implement starts work on its own branch

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md`

- [ ] A step after "Check `## Depends on`": when the current branch is `main` or
  `master`, create the work branch through `/agentdev:git-new-branch`, named
  from the plan key's slug, before executing any task; on any other branch,
  continue where it is

## Spec changes

`spec/git-new-branch` (new):

``` markdown
## ADDED Requirements

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

#### Scenario: The push fails

- **WHEN** the push is rejected or authentication is unavailable
- **THEN** the local branch is kept, the skill reports `PUSH_FAILED`, and no
  API-based ref update is attempted

### Requirement: Existing branches are never reused

The git-new-branch skill SHALL refuse a name that exists as a local branch or
on the remote, and SHALL leave both untouched.

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
lives there, otherwise under the checkout's ignored `.worktrees/` directory,
and SHALL NOT change the current checkout.

#### Scenario: Repository outside /workspaces

- **WHEN** the main checkout is not directly under `/workspaces`
- **THEN** the worktree is created under `<checkout>/.worktrees/` and that
  directory is ignored by Git
```

[IWE workflow skills](../spec/iwe-workflow-skills.md) — Implement SHALL create
the work branch through git-new-branch, named from the plan slug, before
executing the first task when the checkout is on `main` or `master`, and SHALL
continue on the current branch otherwise.

## Verification

- `uv run pytest .agents/plugins/agentdev/tests/test_git_new_branch.py`
- `uv run pytest .agents/plugins/agentdev/tests/test_result_codes.py`
- `shellcheck` on both new scripts (also enforced by pre-commit)
- `uv run validate_agent_files` on every changed `SKILL.md`
- `grep -rn "checkout -b" .agents/plugins/agentdev/skills` finds no
  branch-creation instruction outside `git-new-branch`
- Manual: from `main` with an uncommitted edit, invoke
  `/agentdev:git-new-branch` in a scratch clone and confirm the branch, its
  upstream, and the carried edit

## Out of scope

- Rebase-based workflows; branch creation never rebases local commits
- Deleting or pruning branches and worktrees
- Refreshing `data/codebase/` map docs for the new skill — `/agentdev:iwe-map`
  refresh mode owns that
- Changing `pr-merge` and `pr-merge-chain` coordinator branches, which are
  private disposable refs, not work branches

## Key references

Verified anchor points (line numbers as of 2026-09-28):

- `.agents/plugins/agentdev/skills/update-branch/scripts/update-branch.sh:1` —
  sibling script whose preflight and fetch handling the new script mirrors
- `.agents/plugins/agentdev/skills/update-branch/scripts/__common.sh:15` —
  `require_git_repo`
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:72` —
  `PROTECTED_BRANCH` row
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:112` — "Current branch
  is default" troubleshooting row
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:105` — `PROTECTED_BRANCH`
  row
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:315` — `git checkout -b` in
  the "Not on a feature branch" message
- `.agents/plugins/agentdev/skills/pr-open/scripts/find-branch-pr.sh:106` —
  rejects a branch tracking `main`
- `.agents/plugins/agentdev/skills/git-merge-resolve/SKILL.md:13` — "When to Use
  This Skill" list
- `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md:30` — step 3, "Check
  `## Depends on`"
- `.agents/plugins/agentdev/bin/result-codes.sh:15` — `RESULT_CODES` base table
- `.agents/plugins/agentdev/tests/test_update_branch.py:11` —
  `initialize_repository` fixture pattern
- `.agents/plugins/agentdev/README.md:69` — "Pull requests and git" table
- `.gitignore:11` — `.tmp/` scratch entry
