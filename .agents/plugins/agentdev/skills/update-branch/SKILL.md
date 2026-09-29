---
name: update-branch
description: 'Update the current Git feature branch from a remote base branch by fetching and merging its remote-tracking ref. Use when asked to sync a feature branch, bring a branch up to date with `origin/main`, refresh a stale PR branch, or unblock CI after base-branch drift. Keywords: update branch, sync with origin/main, fetch and merge main, refresh feature branch.'
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/*)
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

## Safety Rules

1. NEVER force-push as part of this workflow.
2. NEVER discard user changes without explicit permission.
3. NEVER change Git configuration or switch remotes.
4. Use local Git commands for branch updates and pushes; never update branch
   refs through a GitHub API or MCP tool.

## Bundled Script

Use [update-branch.sh](scripts/update-branch.sh) instead of running the fetch and
merge commands manually. It:

- checks repository, branch, and working-tree preconditions
- fetches the configured remote
- detects an already-current branch
- delegates the merge to the `git-merge-resolve` bundled script

Options:

- `--remote <name>` selects the remote; default: `origin`.
- `--base <branch>` selects the base branch; default: `main`.

The last line of stdout is always `RESULT=<NAME>`; match on that name, not on a
bare number.

## Workflow 1: Run the Update Script

```bash
${CLAUDE_SKILL_DIR}/scripts/update-branch.sh
```

The script defaults to `origin/main`. Supply `--remote` or `--base` only when
the user requested different values.

## Workflow 2: Handle the Result

| RESULT               | Exit | Meaning                                    | Action                                                                                                                                                          |
| -------------------- | ---- | ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SUCCESS`            | `0`  | The fetch and merge completed              | Continue. The delegated [git-merge-resolve](../git-merge-resolve/SKILL.md) completion workflow still requires reformatting and targeted validation before push. |
| `ALREADY_UP_TO_DATE` | `3`  | The branch already contains the base ref   | Report that the branch is already up to date; make no changes.                                                                                                  |
| `MERGE_CONFLICTS`    | `4`  | The merge stopped on conflicts             | Invoke and complete the [git-merge-resolve](../git-merge-resolve/SKILL.md) conflict-resolution and completion workflows, then return here.                      |
| `PROTECTED_BRANCH`   | `5`  | The current branch is `main` or `master`   | **STOP.** Only with user authorization, create a feature branch through `/agentdev:git-new-branch`, then retry. Do not merge into the default branch.           |
| `FETCH_FAILED`       | `6`  | The configured remote could not be fetched | **STOP.** Report the Git error and restore connectivity or authentication before retrying. Do not change the configured remote to work around the failure.      |
| `PREFLIGHT_ERROR`    | `2`  | Bad usage, not a repo, or a dirty tree     | **STOP.** Fix the reported error before retrying. Do not discard or stash changes without user approval.                                                        |
| `SCRIPT_FAILURE`     | `1`  | The script broke                           | **STOP.** Report the blocker verbatim; do not retry or work around it.                                                                                          |

## Workflow 3: Push the Updated Branch

Only after the `git-merge-resolve` workflow has completed its mandatory
reformat and targeted validation:

1. Confirm the merge result:

   ```bash
   git status --short --branch
   git log --oneline --decorate -n 5
   ```

2. Push through the configured Git remote using local Git:

   ```bash
   git push origin HEAD
   ```

   Replace `origin` with the explicitly selected remote. If push authentication
   is unavailable, stop and report the blocker. Do not fall back to an API-based
   ref update.

## Completion Criteria

- The configured remote was fetched
- The remote base ref is merged into the current branch, or was already merged
- The delegated `git-merge-resolve` workflow resolved all conflicts and ran its
  required reformat and targeted validation
- The updated branch was pushed through local Git when a merge occurred

## Troubleshooting

| Issue                     | Likely Cause                   | Action                                                  |
| ------------------------- | ------------------------------ | ------------------------------------------------------- |
| Dirty working tree        | Local uncommitted changes      | Ask the user to commit or approve a stash workflow      |
| Current branch is default | Incorrect checkout             | With user authorization, use `/agentdev:git-new-branch` |
| Conflicts reported        | Feature and base diverged      | Follow `git-merge-resolve`; do not improvise a shortcut |
| Fetch fails               | Network, remote, or auth issue | Report the error without changing the configured remote |
| Push fails                | Authentication unavailable     | Report the blocker; do not update refs through an API   |
