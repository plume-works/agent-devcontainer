---
name: update-branch
description: 'Update the current Git feature branch: fetch, bring in the commits its own upstream gained on the remote, then merge the remote base branch. Use when asked to sync a feature branch, bring a branch up to date with `origin/main`, refresh a stale PR branch, or unblock CI after base-branch drift. Keywords: update branch, pull branch, sync with origin/main, fetch and merge main, refresh feature branch.'
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/agent-code/*)
---

# Update Branch from origin/main

Fetch a remote base branch, verify whether the current feature branch is behind
it, and delegate merging and conflict resolution to
[git-merge-resolve](../git-merge-resolve/SKILL.md).

## When to Use This Skill

- Sync a feature branch with the latest `origin/main`
- Resolve branch drift causing CI failures or stale diffs
- Refresh a long-lived pull request branch before final review
- Fetch and merge a configurable remote base branch

For a merge that does not require fetching or base-branch synchronization, use
[git-merge-resolve](../git-merge-resolve/SKILL.md) directly.

## Prerequisites

- Git repository with the requested remote configured
- Clean working tree
- Current branch is not `main` or `master`
- User intent is a merge-based update, not a rebase
- Current branch belongs to no GitHub stack (Workflow 0)

## Safety Rules

1. NEVER force-push as part of this workflow.
2. NEVER discard user changes without explicit permission.
3. NEVER change Git configuration or switch remotes.
4. Use local Git commands for branch updates and pushes; never update branch
   refs through a GitHub API or MCP tool.
5. NEVER rebase or reset to bring in the upstream; diverged history is merged.

## Bundled Script

Use [update-branch.sh](agent-code/update-branch.sh) instead of running the fetch and
merge commands manually. It:

- checks repository, branch, and working-tree preconditions
- fetches the configured remote, and the upstream's remote when it differs
- brings in the branch's own upstream first — a fast-forward when the branch
  is only behind it, a merge when the two diverged
- detects a branch that already contains the base ref
- merges the base ref through the `git-merge-resolve` bundled script

The upstream is the branch's configured upstream. The script reports its sync
as `UPSTREAM_ACTION`:

| UPSTREAM_ACTION | When                                                   |
| --------------- | ------------------------------------------------------ |
| `none`          | The branch already contains its upstream               |
| `fast-forward`  | The branch was only behind its upstream                |
| `merge`         | The branch and its upstream diverged                   |
| `untracked`     | The branch has no upstream yet                         |
| `base`          | The upstream is the base ref; the base merge covers it |
| `gone`          | The upstream branch no longer exists on its remote     |

On `gone` the script prints a warning and continues; the push in Workflow 3
recreates the remote branch.

Options:

- `--remote <name>` selects the remote; default: `origin`.
- `--base <branch>` selects the base branch; default: `main`.

The last line of stdout is always `RESULT=<NAME>`; match on that name, not on a
bare number.

## Workflow 0: Refuse a Stack Branch

A branch of a GitHub stack is rewritten by GitHub's post-merge rebase, so a
merge-based update diverges from it. Check before running the script:

```bash
pr=$(gh pr view --json number --jq .number 2>/dev/null) &&
  gh api "repos/{owner}/{repo}/pulls/$pr" --jq '.stack.number // empty'
gh stack view --json >/dev/null 2>&1 && echo "tracked in a local stack"
```

If either prints anything, **STOP** without merging: the branch belongs to a
stack. Report that it is updated with the guarded refresh of
[gh-stack](../gh-stack/SKILL.md) instead: `begin`, `gh stack rebase`, then
`publish`. A branch with no open pull request and
no local stack continues to Workflow 1.

## Workflow 1: Run the Update Script

```bash
agent-code/update-branch.sh
```

The script defaults to `origin/main`. Supply `--remote` or `--base` only when
the user or the calling skill supplies different values.

## Workflow 2: Handle the Result

| RESULT               | Exit | Meaning                                                              | Action                                                                                                                                                          |
| -------------------- | ---- | -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SUCCESS`            | `0`  | The update created a merge commit                                    | Continue. The delegated [git-merge-resolve](../git-merge-resolve/SKILL.md) completion workflow still requires reformatting and targeted validation before push. |
| `ALREADY_UP_TO_DATE` | `3`  | The branch already contains the base ref; no merge commit was needed | Report that the branch is already up to date. A fast-forward to its upstream may have moved it; there is nothing new to push.                                   |
| `MERGE_CONFLICTS`    | `4`  | A merge stopped on conflicts; `SOURCE` names the ref being merged    | Invoke and complete the [git-merge-resolve](../git-merge-resolve/SKILL.md) conflict-resolution and completion workflows, then rerun Workflow 1.                 |
| `PROTECTED_BRANCH`   | `5`  | The current branch is `main` or `master`                             | **STOP.** Only with user authorization, create a feature branch through `/agentdev:git-new-branch`, then retry. Do not merge into the default branch.           |
| `FETCH_FAILED`       | `6`  | The configured remote could not be fetched                           | **STOP.** Report the Git error and restore connectivity or authentication before retrying. Do not change the configured remote to work around the failure.      |
| `PREFLIGHT_ERROR`    | `2`  | Bad usage, not a repo, or a dirty tree                               | **STOP.** Fix the reported error before retrying. Do not discard or stash changes without user approval.                                                        |
| `SCRIPT_FAILURE`     | `1`  | The script broke                                                     | **STOP.** Report the blocker verbatim; do not retry or work around it.                                                                                          |

### Rerun After a Conflict

Each run stops at the first conflicted merge, so one run never resolves two.
After git-merge-resolve commits a resolution, run Workflow 1 again: when the
conflict was in the upstream merge, the rerun goes on to merge the base.
Repeat until the script returns `SUCCESS` or `ALREADY_UP_TO_DATE`. An
`ALREADY_UP_TO_DATE` that follows a resolved conflict still leaves a new merge
commit on the branch — continue to Workflow 3.

## Workflow 3: Push the Updated Branch

Only after the `git-merge-resolve` workflow has completed its mandatory
reformat and targeted validation:

1. Confirm the merge result:

   ```bash
   git status --short --branch
   git log --oneline --decorate -n 5
   ```

2. Push with the [pr-open](../pr-open/SKILL.md) push helper,
   `agent-code/push-branch.sh`, and handle its result exactly as that skill's
   step 8 describes — including `MAP_STALE`, which refreshes the codebase map
   and pushes again. Pass `--remote` only for an explicitly selected remote. If
   push authentication is unavailable, stop and report the blocker. Do not fall
   back to an API-based ref update.

## Completion Criteria

- The configured remote, and the upstream's remote when it differs, were fetched
- The branch's upstream, when it has one, was fast-forwarded or merged before
  the base
- The remote base ref is merged into the current branch, or was already merged
- The delegated `git-merge-resolve` workflow resolved all conflicts and ran its
  required reformat and targeted validation
- The updated branch was pushed through local Git when a merge occurred

## Troubleshooting

| Issue                     | Likely Cause                                     | Action                                                              |
| ------------------------- | ------------------------------------------------ | ------------------------------------------------------------------- |
| Dirty working tree        | Local uncommitted changes                        | Ask the user to commit or approve a stash workflow                  |
| Current branch is default | Incorrect checkout                               | With user authorization, use `/agentdev:git-new-branch`             |
| Conflicts reported        | Feature and base diverged                        | Follow `git-merge-resolve`; do not improvise a shortcut             |
| Fetch fails               | Network, remote, or auth issue                   | Report the error without changing the configured remote             |
| Push fails                | Authentication unavailable                       | Report the blocker; do not update refs through an API               |
| Branch belongs to a stack | Stacked pull request                             | Stop; refresh it with the gh-stack skill's guard instead            |
| Upstream reported `gone`  | Remote branch deleted, often after its PR merged | Confirm the PR is still open before Workflow 3 recreates the branch |
