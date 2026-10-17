---
name: gh-stack
description: >
  Manages stacked PRs and splits multi-part work into reviewable branches with gh-stack, publishing
  every stack branch through a guard that never drops commits pushed from elsewhere. Use for stack
  creation, viewing, edits, push, submit, sync, rebase, merge, or checkout; when asked to split or
  isolate work for review; whenever a user mentions a stack, branch layers, dependent PRs, or
  gh stack; or when a stack is checked out.
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/agent-code/*)
---

# gh-stack

`gh stack` is a [GitHub CLI](https://cli.github.com/) extension for stacked branches and pull
requests. A stack is an ordered chain of branches rooted on a trunk, where each branch has one PR
based on the branch below it, so a reviewer sees only that layer's diff.

`gh stack` prints a stack trunk-first, left to right:

```
(main) <- auth <- api <- frontend
```

Left is the **bottom**, right is the **top**. `auth` is based on `main` and merges first;
`frontend` merges last. `up` moves toward the top, away from trunk; `down` moves toward it.
Foundational work belongs at the bottom, code that depends on it above. For how to choose the
layers, read `references/upstream/stack-design.md`.

## The push guard

`gh stack push`, `submit`, and `sync` fetch each layer and then take their `--force-with-lease`
from the ref they just fetched, so a stale local layer silently replaces commits pushed from
elsewhere. Every remote update of a stack therefore goes through
[stack-guard.sh](agent-code/stack-guard.sh):

- `agent-code/stack-guard.sh begin` — before anything rewrites the stack: the first commit on a
  layer, a `gh stack rebase`, or adopting an existing branch.
- `agent-code/stack-guard.sh publish` — in place of `gh stack push`.
- `agent-code/stack-guard.sh publish --submit` — in place of `gh stack submit --auto`.

Never run a bare `gh stack push`, `gh stack submit`, or `gh stack sync`. This overrides every
mention of them in `references/upstream/`. `gh stack rebase` never pushes and stays allowed.
Pass `--remote <name>` to the guard when the repository has more than one remote and
`remote.pushDefault` is unset.

The last stdout line is `RESULT=<NAME>`:

| RESULT                | Exit   | Action                                                                                                                                                                                       |
| --------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SUCCESS`             | `0`    | `begin`: when `FAST_FORWARDED=<layer>` names a layer below the top, run `gh stack rebase` before editing. `publish`: every layer is on the remote.                                           |
| `REMOTE_ONLY_COMMITS` | `3`    | **STOP.** Show the commits from stderr and ask the user how to incorporate them. Nothing changed. Rerun `begin` once the local layer contains them.                                         |
| `REMOTE_MOVED`        | `4`    | **STOP.** Someone pushed a layer during your edit; nothing was pushed. Show the layer and SHAs, and ask the user how to combine the new remote commits with yours before running `begin` again. |
| `PUSH_FAILED`         | `5`    | Report the `gh stack` error from stderr. Fix its cause, then rerun `publish`; the `begin` record is kept.                                                                                   |
| `PUSH_INCOMPLETE`     | `6`    | Report the layers stderr names. Rerun `publish` once; if it repeats, **STOP** and report.                                                                                                  |
| `REMOTE_OVERWRITTEN`  | `7`    | **STOP.** A push landed between the check and the push and was overwritten. Show the lost commits stderr names, cherry-pick them by SHA (still in the tracking ref's reflog) with the user's consent, then run `begin` again. |
| `PREFLIGHT_ERROR`     | `2`    | **STOP.** Report the error verbatim: not a repo, not in a stack, detached HEAD, fetch failure, or a layer checked out with changes that block its fast-forward.                             |
| `SCRIPT_FAILURE`      | `1`    | **STOP.** Report the blocker verbatim; do not retry or work around it.                                                                                                                       |
| `SIGNAL_*`            | `129`+ | **STOP.** Inspect `git status` before rerunning.                                                                                                                                             |

`begin` records each layer's remote tip in `./.tmp/gh-stack-guard/tips`, adding `.tmp/` to
`.git/info/exclude` when Git does not already ignore it; `publish` compares
against that record and refreshes it after a verified push. Without the record, `publish` refuses
any layer whose remote holds a patch the local branch lacks — which also refuses a layer whose
rebase conflict you resolved, so run `begin` first.

## Setup

The image ships the pinned `gh-stack` extension; elsewhere, install it with
`gh extension install github/gh-stack`. It requires Git 2.36+ and an authenticated GitHub CLI.

```bash
git config rerere.enabled true         # remember conflict resolutions
git config remote.pushDefault origin   # required if the repo has more than one remote
```

## Non-interactive use

`gh stack` branches on whether **stdout is a TTY**. Piped, most commands error cleanly or print
static text; under a PTY the same commands open a prompt or a full-screen TUI and block forever.
Agent harnesses differ, so always pass the flags below instead of relying on that detection.

**Multiple remotes:** never run `rebase` or `link` without `--remote <name>` unless
`remote.pushDefault` is configured. `checkout` and `trunk` have no `--remote` flag and require the
config.

| Always run | Never run bare | Why |
|---|---|---|
| `gh stack view --json` | `gh stack view` | opens a TUI under a PTY |
| `stack-guard.sh publish --submit` | `gh stack submit` | prompts for a title per new PR; unguarded |
| `gh stack merge <target> --yes` | `gh pr merge` | `gh pr merge` cannot merge a stack |
| `gh stack init <branch>...` | `gh stack init` | prompts for branch names |
| `gh stack add <branch>` | `gh stack add` | prompts for a name, and fails even when piped |
| `gh stack checkout <target>` | `gh stack checkout` | opens a selection menu |
| `gh stack up` / `down` / `top` / `bottom` | `gh stack switch` | `switch` is menu-only |
| — | `gh stack modify` | TUI-only, no non-interactive path |

- `view --short` is safe in both modes, but it is formatted for humans. Use `--json` to parse.
- **`checkout <pr>` when a different local stack already covers those branches** cannot be forced.
  Run `gh stack unstack --local` first (this keeps the stack on GitHub), then retry.
- **Worktrees:** local stacks share one common-directory catalog. Use `--print-path` with
  navigation or explicit-target `checkout` to locate a foreign-owned branch without stealing its
  checkout. Check the exit status before changing directories; parse only successful path-mode
  stdout, never status messages.

## Creating a stack

Create the stack before writing files. Do not implement every concern on trunk and split it
later. Put one dependent concern in each layer, bottom to top. Branch names are verbatim —
`gh stack add refactor/foo` creates `refactor/foo`.

```bash
gh stack init auth                      # create the stack and check out its branch
agent-code/stack-guard.sh begin
git add ... && git commit -m "Add auth middleware"
gh stack add api                        # next layer, branched from the current one
git add ... && git commit -m "Add API routes"
agent-code/stack-guard.sh publish --submit   # push every branch and open draft PRs
gh stack view --json                    # confirm
```

`publish --submit` opens draft PRs whose body is the repository's PR template; give every layer a
real description with `gh pr edit` before review.

**Adopting a branch that already exists on the remote:** `gh stack init` creates a missing local
branch at the trunk tip, and the next push would replace the real branch and close its PR. Create
the local branch from the remote first, and run `begin` right after `init`:

```bash
git switch <branch>                     # creates it from <remote>/<branch>
gh stack init <branch>
agent-code/stack-guard.sh begin
```

## Editing an existing stack

Check out the layer that owns the change before editing. Never commit a lower layer's concern on
the current top branch. Run `gh stack view --json`; if ownership is unclear, inspect
`git log --all -- <path>`.

```bash
agent-code/stack-guard.sh begin         # before the first commit
gh stack down                           # or: gh stack checkout api
git add ... && git commit -m "Add get-user endpoint"
gh stack rebase --upstack               # replay every branch above onto the change
gh stack top                            # return to where you were
agent-code/stack-guard.sh publish
```

## Refreshing the stack

After a layer merges, or when the trunk moved, rebase the remaining layers onto the trunk:

```bash
agent-code/stack-guard.sh begin
gh stack rebase                         # fetch, fast-forward, skip merged layers, rebase; no push
agent-code/stack-guard.sh publish
```

`begin` accepts a layer that GitHub rebased after a lower layer merged, because its remote holds
no patch the local branch lacks. `gh stack rebase` replaces `gh stack sync` here: `sync` pushes
by itself, unguarded, and exits 0 even when its push fails.

## Merging

Scope the merge with an argument:

```bash
gh stack merge 42 --yes          # PR #42 plus every unmerged PR below it
gh stack merge 7 --yes           # every unmerged PR in stack #7
gh stack merge 42 --yes --squash # or --merge, --rebase, --merge-method <method>
```

Pass a PR number to merge that PR and every unmerged PR below it, or a stack number to merge every
unmerged PR in that stack. The operation is all-or-nothing: if any PR in that set cannot merge,
none do. A draft cannot merge; mark it ready first.

Without a method flag the last-used method is reused. If the base branch uses a merge queue, the
stack is queued instead and the queue picks the method, ignoring any flag you passed with a
warning; queued PRs may land in separate groups.

## Reading state

`gh stack view --json` writes JSON to **stdout**. Status messages go to **stderr** — do not parse
them, branch on exit codes instead.

```
trunk           string
currentBranch   string
branches[]      name, head, base, isCurrent, isMerged, isQueued, needsRebase
branches[].pr   number, url, state ("OPEN" | "MERGED" | "QUEUED"); absent when no PR exists
```

`base` is the saved SHA of the parent branch that this branch was last known to contain. It may be
older than the parent's current tip. `needsRebase` is true when the current parent tip is no longer
an ancestor of the branch.

## Exit codes

| Code | Meaning | Recovery |
|---|---|---|
| 0 | Success | — |
| 1 | Generic error | Read stderr |
| 2 | Not in a stack | `gh stack init`, or `gh stack checkout <target>` |
| 3 | Rebase conflict | Resolve the files, `git add`, then `gh stack rebase --continue`; `--abort` restores the stack |
| 4 | GitHub API failure | Check `gh auth status`, retry |
| 5 | Invalid arguments | Fix the invocation; see `<command> --help` |
| 6 | Disambiguation required | Branch is in several stacks; check out a non-shared branch |
| 7 | Rebase already in progress | `gh stack rebase --continue` or `--abort` |
| 8 | Stack file locked | Another `gh stack` process is writing; retry after ~5s |
| 9 | Stacked PRs unavailable | Not enabled on the repository; tell the user |
| 10 | Modify recovery required | `gh stack modify --abort` |

After a resolved conflict, `publish` as usual: the `begin` record from before the rebase is still
the lease.

## Constraints

- Stacks are strictly linear: one parent, at most one child. Use separate stacks for parallel work.
- `rebase` automatically updates affected clean worktrees; it never auto-stashes or creates or
  removes worktrees. Mutations serialize across the clone, and paused operations require recovery
  in their recorded owners.
- There is no non-interactive reorder or removal. Errors may suggest `gh stack modify`, but it is
  TUI-only — restructure with `unstack` then `init` instead.
- PR titles and bodies are auto-generated. Use `gh pr edit` afterwards to change them.

## More detail

`gh stack <command> --help` is authoritative for flags and arguments. Note that
`gh stack help <command>` does **not** work — it prints the top-level help.

`references/upstream/` holds GitHub's own reference pages for the pinned release, unchanged and
under their MIT [LICENSE](references/upstream/LICENSE); the non-interactive guidance above is
adapted from the same source. Open the page whose trigger matches the task, and apply the push
guard wherever a page says to push or sync:

- `references/upstream/stack-design.md` — read before creating a stack, when deciding how many
  layers to use, what belongs in each one, or whether work belongs in a new stack.
- `references/upstream/commands.md` — read when a command fails unexpectedly or you need its
  preconditions, side effects, atomicity, or ordering guarantees.
- `references/upstream/troubleshooting.md` — read on a rebase conflict, after a squash-merge, on
  local and remote divergence, when restructuring a stack, or when driving stacks from another
  tool.
