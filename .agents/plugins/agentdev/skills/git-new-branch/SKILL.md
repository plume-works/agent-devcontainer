---
name: git-new-branch
description: 'Create a new Git work branch at the freshly fetched remote base, push it at once so it tracks its own upstream, and carry uncommitted changes onto it — optionally in a separate worktree. Use when asked to start a feature branch, create or cut a branch, get off main before working, or when another skill says to switch to a feature branch. Keywords: new branch, create branch, feature branch, start work, git switch -c, git worktree, branch from origin/main.'
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/*)
---

# Create a Work Branch

Start new work on a branch that begins at the just-fetched remote base and
tracks `<remote>/<name>` — never the base itself — so `git pull`,
[update-branch](../update-branch/SKILL.md), and [pr-open](../pr-open/SKILL.md)
all treat it as a feature branch from its first minute.

## When to Use This Skill

- Start a feature branch before writing code, or move off `main` or `master`
- Another skill stopped with `PROTECTED_BRANCH` and the user authorized a new
  branch
- Work on a second branch in parallel without touching the current checkout
  (worktree mode)

To bring an existing branch up to date with its base, use
[update-branch](../update-branch/SKILL.md) instead.

## Safety Rules

1. NEVER reset, reuse, or overwrite an existing branch, local or remote. The
   one exception is the script's own reset of local `main`/`master` once its
   commits are on the new branch (Workflow 5); never reset it by hand.
2. NEVER force-push.
3. NEVER stash, discard, or move user changes without explicit approval.
4. NEVER change Git configuration or switch remotes.
5. Push with local Git only; never create or update branch refs through a
   GitHub API or MCP tool.

## Choose the Name

Use the name the user gives. When they give none, suggest one from context and
confirm it before running the script:

| Context                                | Suggested name                         |
| -------------------------------------- | -------------------------------------- |
| An IWE plan `data/plans/<date>-<slug>` | `<slug>`                               |
| A GitHub issue                         | `<number>-<slug>`                      |
| Anything else                          | a short kebab-case summary of the work |

`<slug>` for an issue is a short kebab-case form of its title.

## Bundled Script

Use [git-new-branch.sh](scripts/git-new-branch.sh) instead of running the
branch commands manually. It:

- validates the name with `git check-ref-format --branch`
- fetches the remote and resolves `<remote>/<base>`; when `<base>` does not
  exist, it falls back to the branch `refs/remotes/<remote>/HEAD` names, or,
  when that symref is unset, to the default branch `gh repo view` reports for
  the remote's URL
- refuses a name that exists locally or on the remote
- creates the branch with `--no-track` at the fetched base, carrying
  uncommitted and untracked changes when no changed path differs between HEAD
  and the base
- on `main` or `master` with commits the base lacks, starts the branch at
  `HEAD` instead, so those commits move onto it, reports `LOCAL_COMMITS`, and —
  outside worktree mode — resets the default branch to the base
- pushes with `--set-upstream` so the branch tracks `<remote>/<name>`

Options:

- `--remote <name>` selects the remote; default: `origin`.
- `--base <branch>` selects the base branch; default: `main`.
- `--stash` stashes local changes (untracked included), creates and pushes the
  branch, then pops them onto it. Pass it only after the user approves.
- `--worktree` creates the branch in a new worktree `<repo>-<branch>` (a `/`
  in the branch stays a directory separator) and leaves the current checkout
  alone. Its parent is
  `/workspaces` when the main checkout lives directly under `/workspaces`,
  otherwise `<main checkout>/.worktrees/`, which the script adds to
  `.git/info/exclude` unless Git already ignores it.
- `--worktree-root <dir>` overrides the worktree parent and implies
  `--worktree`.

Supply `--remote`, `--base`, or a worktree option only when the user asked for
it. The last line of stdout is always `RESULT=<NAME>`; match on that name, not
on a bare number.

## Workflow 1: Create the Branch

```bash
${CLAUDE_SKILL_DIR}/scripts/git-new-branch.sh <name>
```

## Workflow 2: Handle the Result

| RESULT            | Exit                | Meaning                                                              | Action                                                                                                                                                                  |
| ----------------- | ------------------- | -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SUCCESS`         | `0`                 | Branch created at `BASE_SHA`, pushed, tracking `<remote>/<name>`     | Report `BRANCH`, `BASE`, and `WORKTREE` when present. In worktree mode, continue the work inside `WORKTREE`. When `LOCAL_COMMITS` is printed, continue with Workflow 5. |
| `BRANCH_EXISTS`   | `3`                 | The name exists locally or on the remote; nothing was created        | **STOP.** Ask the user for another name, or whether to continue on the existing branch with `git switch <name>`. Never reset it.                                        |
| `CARRY_CONFLICT`  | `4`                 | Local changes touch paths that differ between HEAD and the base      | Show the paths from stderr and ask the user (Workflow 3). Nothing was changed.                                                                                          |
| `PUSH_FAILED`     | `5`                 | The branch exists locally but the push failed                        | **STOP.** Report the Git error. The local branch is kept; retry `git push --set-upstream <remote> <name>` once access is restored — never via API.                      |
| `FETCH_FAILED`    | `6`                 | The remote could not be fetched                                      | **STOP.** Report the Git error; restore connectivity or authentication. Do not change the configured remote.                                                            |
| `STASH_CONFLICTS` | `7`                 | The branch was created but popping the stash conflicted              | Resolve through Workflow 4. The stash entry `STASH_REF` is kept until then.                                                                                             |
| `CREATE_FAILED`   | `8`                 | The branch could not be created; the checkout is unchanged           | **STOP.** Report the Git error. Any stash was restored; when `STASH_REF` is printed, tell the user that stash entry holds their changes.                                |
| `PREFLIGHT_ERROR` | `2`                 | Bad usage, not a repository, invalid name, or no base ref to resolve | **STOP.** Report the error verbatim and fix the input before retrying.                                                                                                  |
| `SCRIPT_FAILURE`  | `1`                 | The script broke                                                     | **STOP.** Report the blocker verbatim; do not retry or work around it.                                                                                                  |
| `SIGNAL_*`        | `129`, `130`, `143` | Interrupted by HUP, INT, or TERM                                     | **STOP.** Inspect `git status` and `git stash list` before rerunning.                                                                                                   |

## Workflow 3: Uncommitted Changes Git Cannot Carry

On `CARRY_CONFLICT`, ask the user with the structured-question tool:

- **Stash and retry** — rerun the same command with `--stash`.
- **Cancel** — leave the checkout and changes as they are.

Committing the changes first, or using `--worktree`, are also valid answers
when the user offers them.

## Workflow 4: Resolve a Conflicted Stash Pop

On `STASH_CONFLICTS`, the new branch is checked out and the popped changes
conflict with the base. The stash entry `STASH_SHA`, listed as `STASH_REF` when
the script finished, still holds them. Other sessions share the stash stack, so
re-find its current `stash@{n}` with `git stash list --format='%gd %H'` before
each command that names it.

1. Resolve every conflicted path with the
   [git-merge-resolve](../git-merge-resolve/SKILL.md) "Resolve Conflicts"
   workflow. Stage `:2` is the base, stage `:3` the stashed change.
2. Stage the resolutions with `git add <path>`, then unstage them with
   `git restore --staged <path>` so they remain ordinary uncommitted changes.
   Do not commit: there is no merge to complete.
3. Confirm that no unresolved path or conflict marker remains:

   ```bash
   git diff --name-only --diff-filter=U
   ```

4. Confirm that every stashed change was recovered. A failed pop can skip a
   stashed untracked file without leaving an unmerged path, for example when
   the base now tracks the same path. List what the entry holds:

   ```bash
   git stash show --include-untracked --name-only <STASH_SHA>
   ```

   Every listed path must hold the stashed change or its resolution. For a
   skipped untracked file, show the user `git show <STASH_SHA>^3:<path>` and
   ask how to combine it with the base's version. Do not continue until each
   path is accounted for.

5. Drop the entry only after steps 3 and 4 pass:

   ```bash
   git stash drop <current stash@{n} of STASH_SHA>
   ```

If stderr also reported a failed push, handle it as `PUSH_FAILED` afterwards.

## Workflow 5: Merge the Base After Moving Commits

When `SUCCESS` also printed `LOCAL_COMMITS=<n>`, the branch starts at the
default branch's local `HEAD` and does not yet contain `BASE`. Outside worktree
mode the script has already reset local `main` (or `master`) to `BASE`, since
the commits now live on the new branch.

1. Work on the new branch — inside `WORKTREE` when it was printed.
2. If `git status --porcelain` is not empty, ask the user to commit the changes
   or approve a stash first; never stash without approval.
3. Run `/agentdev:update-branch` to merge `BASE` into the branch, and follow its
   result table, including conflict resolution and the push.
4. In worktree mode, local `main` is still checked out in the original checkout
   and still holds the `<n>` commits. Tell the user; resetting it there is
   their call, never yours.

## Completion Criteria

- The branch points at the freshly fetched base commit `BASE_SHA`, or, after
  `LOCAL_COMMITS`, contains both the moved commits and `BASE`
- `git rev-parse --abbrev-ref @{u}` on the branch prints `<remote>/<name>`
- The user's uncommitted changes are present on the branch, and any stash this
  skill created has been dropped only after its conflicts were resolved
