---
name: pr-restack-all
description: "Restack a chain of manual stacked pull requests with merges after a lower one changed or squash-merged: merge an open predecessor's head, or reconnect a merged predecessor through its final head and squash commit, bottom to top, from a detached worktree, with plain pushes only. Use after a pull request in a chain merges, when a dependent pull request falls behind the one below it, or when pr-open or pr-merge-stack asks for a restack. Keywords: restack, stacked pull requests, dependent PR, reconnect after squash merge, Depends on."
---

# Restack Manual Stacked Pull Requests

A dependent pull request is based on its predecessor's branch and lists it
under `## Depends on`. When the predecessor moves, the dependent branch merges
it; when the predecessor squash-merges, the dependent branch is reconnected so
its diff against `main` shrinks to its own work. No branch is ever rebased,
reset, or force-pushed.

## When to Use This Skill

- A pull request in a chain was squash-merged and the ones above it still carry
  its commits
- A lower pull request gained commits the ones above it lack
- [pr-open](../pr-open/SKILL.md) or [pr-merge-stack](../pr-merge-stack/SKILL.md)
  asks for a restack

To bring a single branch up to date with `main`, use
[update-branch](../update-branch/SKILL.md): a restack never merges `main`.

## The Script

`pr_restack_all.py` ships in the plugin's `bin/`, which is on `PATH` while the
plugin is enabled. Run it from the repository root.

```bash
pr_restack_all.py <top-pr>          # a chain, from its top pull request
pr_restack_all.py <branch>          # a branch, with or without a pull request
pr_restack_all.py <branch> --list   # print the branch's own dependencies only
```

`--remote <name>` selects the remote (default `origin`); `--trunk <branch>`
names the branch a chain bottoms out on (default: the remote's default branch).
Supply either only when the user asked for it.

### A Chain From Its Top Pull Request

1. The chain is walked down: each pull request's base is its predecessor's head
   branch, and the open pull request with that head is the next link. A base
   of the trunk is the bottom. Each link's last `## Depends on` entry must be
   the pull request below it.
2. One fresh detached worktree under `./.tmp/` is built from remote refs. No
   local branch is checked out, created, or moved, so other sessions'
   worktrees are untouched; a session whose branch was advanced sees an
   ordinary non-fast-forward rejection and merges.
3. Bottom to top, each pull request acts only on its nearest predecessor P, the
   last entry of its `## Depends on`:
   - P open: P's head branch is merged in.
   - P merged, its squash commit already in the branch: nothing to do.
   - P merged otherwise: **reconnect**. P's final head (`headRefOid`) and its
     squash commit (`mergeCommit.oid`) come from P's metadata, and
     `refs/pull/<P>/head` must equal that head. The squash commit is merged
     into a detached copy of the head, never pushed, and the copy is merged
     into the branch. The entry is then rewritten in place as
     `- #<P> — merged as <MERGE> (head <HEAD>), reconnected`.
   - P closed without merging: stop.
4. Each branch that moved is pushed without force.

### A Branch

The dependencies are the branch's own `Depends-on: #<P>` trailers, the ones
[git-new-branch](../git-new-branch/SKILL.md) `--depends-on` writes. Trailers
carried in from a predecessor's own branch are not counted. Every merged
dependency is reconnected as above, the branch is pushed without force, and,
when the branch has an open pull request, each reconnected entry gets its merge
record.
`--list` prints `DEPENDENCY=#<P> <STATE> <head-branch>` per dependency, oldest
first, and changes nothing.

## Handle the Result

The last stdout line is `RESULT=<NAME>`. Other lines: `CHAIN=#a,#b` bottom to
top, `RECONNECTED=#P HEAD=<HEAD> MERGE=<MERGE>` per reconnect,
`PUSHED=<branch> <sha>` per branch that moved, and `WORKTREE=<path>` on a
conflict.

| RESULT               | Exit | Meaning                                                            | Action                                                                                                        |
| -------------------- | ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| `SUCCESS`            | `0`  | Every pull request is restacked                                    | Report the chain, reconnects, and pushes.                                                                     |
| `PREFLIGHT_ERROR`    | `2`  | Bad usage, not a repository, or the branch does not exist          | **STOP.** Fix the input.                                                                                      |
| `GH_FAILED`          | `3`  | `gh` could not read or edit a pull request                         | **STOP.** Report the error; restore `gh` authentication.                                                      |
| `CHAIN_BROKEN`       | `4`  | A link is not open, missing, in a fork, or its last entry is wrong | **STOP.** Report which link; fix its base or its `## Depends on` section; a fork's branch is never restacked. |
| `PREDECESSOR_CLOSED` | `5`  | A predecessor was closed without merging                           | **STOP.** Ask the user how the dependent work continues.                                                      |
| `HEAD_MISMATCH`      | `6`  | `refs/pull/<P>/head` differs from P's recorded final head          | **STOP.** Report both commits; never reconnect against a guessed head.                                        |
| `MERGE_CONFLICT`     | `7`  | A merge conflicted; the worktree is kept at `WORKTREE`             | Resolve the conflict in the worktree (below), push, and rerun.                                                |
| `PUSH_REJECTED`      | `8`  | A plain push was rejected because the branch moved                 | Rerun: the restack starts again from the new remote state.                                                    |
| `FETCH_FAILED`       | `9`  | The remote could not be fetched                                    | **STOP.** Restore connectivity or authentication.                                                             |
| `BODY_UPDATE_FAILED` | `10` | The push landed but the merge record was not written               | Rerun: a branch holding both P's head and squash commit gets its missing record.                              |
| `SCRIPT_FAILURE`     | `1`  | The script broke                                                   | **STOP.** Report the blocker verbatim.                                                                        |

## Resolve a Conflict and Rerun

1. In `WORKTREE`, resolve every conflicted path with the
   [git-merge-resolve](../git-merge-resolve/SKILL.md) "Resolve Conflicts"
   workflow and commit the merge.
2. Push with the command the error printed:
   `git push <remote> HEAD:refs/heads/<branch>` — a plain push, never forced.
3. Remove the worktree with `git worktree remove <WORKTREE>`, then rerun the
   same command. Pull requests already restacked are skipped: an open
   predecessor's head or a merged one's squash commit is already in them.

## Rules

- Never merge `main` here; catching up with `main` is a separate
  [update-branch](../update-branch/SKILL.md) run.
- Never rebase, reset, or force-push a branch.
