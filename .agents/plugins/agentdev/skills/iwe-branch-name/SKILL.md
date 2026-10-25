---
name: iwe-branch-name
description: "Name the next work branch for an IWE plan — impl/<slug>/iteration-<N> or ship/<slug>/iteration-<N> — counting every iteration already used locally, on the remote, and in pull requests of any state, and read the plan's state at the remote default branch to pick the phase. Use when starting implementation or shipping work for a plan, when a skill needs the plan's next branch name, or to tell whether a branch is a plan work branch. Creates no branch: callers pass the name to git-new-branch. Keywords: plan branch name, iteration, impl branch, ship branch, next branch, plan state."
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/agent-code/*)
---

# Name a Plan's Work Branch

A plan's work spans several pull requests — one or more for implementation,
one for shipping — and each starts on a fresh branch off the default branch.
The repository squash-merges and deletes head branches, so the next iteration
number has to be recovered from everywhere an earlier one may survive.

## The Name Shape

`<phase>/<slug>/iteration-<N>`:

- `phase` is `impl` or `ship`;
- `slug` is the plan key's file name without its `YYYYMMDD-` prefix
  (`data/plans/20261020-foo` → `foo`);
- `N` is a positive integer, one more than the highest already used for that
  phase and slug.

The `iteration-<N>` suffix is always present, even on the first branch. Git
cannot hold a ref beside another it would nest under — `ship/foo` blocks
`ship/foo/iteration-2` — and a name that always ends in `iteration-<N>` is
never a path prefix of another.

## Bundled Script

Use [iwe-branch-name.py](agent-code/iwe-branch-name.py); run it from the
repository root. It imports only the standard library and changes no branch.

- `parse <branch>` splits a name into `PHASE`, `SLUG`, and `ITERATION`. A name
  off the shape, including a bare `<slug>` from before this convention, is
  `NOT_A_WORK_BRANCH`.
- `plan-state <plan-key|slug>` fetches the remote's default branch, finds
  `data/plans/*-<slug>.md` in that tree — never the working tree — and prints
  `DEFAULT_BRANCH`, `PLAN_KEY`, and `PLAN_STATE`: `missing`, `cancelled`,
  `done`, `complete`, or `incomplete`. A plan with no `stage` is `complete`
  when it has at least one task checkbox under `## Implementation Steps` or
  the older `## Tasks` heading and every one is ticked; a plan with no task
  checkbox is `incomplete`, so `next` never sends it to `ship`.
- `next <plan-key|slug>` prints `NEXT`, `NEXT_KIND` (`default`, `impl`,
  `ship`), and `ITERATION` for a work branch. With `--phase impl|ship` it names
  the next iteration of that phase without reading the plan; without it, the
  phase follows `plan-state`: `complete` → `ship`, `incomplete` → `impl`, and
  `done`, `cancelled`, or `missing` → the default branch, with the plan-state
  keys printed too.

The iteration counts local branches, the remote's branches, and the pull
requests in any state of the repository the remote's URL names, through
`gh pr list --repo <remote URL>`, so branches and pull requests always come from
the same repository. When `gh` cannot answer — missing, unauthenticated, or a
remote that is not on GitHub — `next` reports `GH_UNAVAILABLE` rather than a
number a merged pull request may already hold.

`<plan-key|slug>` takes `data/plans/<date>-<slug>`, `<date>-<slug>`, or a bare
`<slug>`. `--remote <name>` selects the remote; default: `origin`. Supply it
only when the user asked for another remote.

Pass `--phase` whenever the caller already knows the phase. A plan written on
the current checkout but not yet merged reads as `missing` at the remote
default branch, so only `--phase` names its branch.

```bash
agent-code/iwe-branch-name.py next data/plans/20261020-foo --phase impl
```

The last line of stdout is always `RESULT=<NAME>`; match on that name, not on
a bare number.

## Handle the Result

| RESULT              | Exit                | Meaning                                                                              | Action                                                                                                                        |
| ------------------- | ------------------- | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `SUCCESS`           | `0`                 | The name's parts, the plan's state, or the next name was printed                     | Use the keys. For `next`, create a work branch through `/agentdev:git-new-branch NEXT`; on `NEXT_KIND=default`, switch to it. |
| `NOT_A_WORK_BRANCH` | `3`                 | `parse`: the branch is not `<impl\|ship>/<slug>/iteration-<N>`                       | Treat the branch as not a plan work branch. It is never renamed.                                                              |
| `AMBIGUOUS_PLAN`    | `4`                 | The slug matches more than one dated plan at the remote default branch               | **STOP.** Show the candidates from stderr and rerun with the full plan key the user means.                                    |
| `FETCH_FAILED`      | `5`                 | The remote could not be fetched or its branches listed                               | **STOP.** Report the Git error; restore connectivity or authentication. Do not change the configured remote.                  |
| `GH_UNAVAILABLE`    | `6`                 | `gh` is missing, unauthenticated, or could not read the remote's pull requests       | **STOP.** Ask the user to install or log in to `gh` (`gh auth status`). Never pick an iteration without it.                   |
| `PREFLIGHT_ERROR`   | `2`                 | Bad usage, not a repository, no `.iwe/config.toml`, unknown remote or default branch | **STOP.** Report the error verbatim and fix the input before retrying.                                                        |
| `SCRIPT_FAILURE`    | `1`                 | The script broke                                                                     | **STOP.** Report the blocker verbatim; do not retry or work around it.                                                        |
| `SIGNAL_*`          | `129`, `130`, `143` | Interrupted by HUP, INT, or TERM                                                     | **STOP.** Nothing was changed; rerun when ready.                                                                              |

## Rules

- This skill names branches; it never creates, switches, or deletes one.
  Create the branch through `/agentdev:git-new-branch`, which owns branch
  creation and its push.
- Never hand-pick an iteration number or reuse a name `next` did not print.
- Never rename or migrate a branch named before this shape.
