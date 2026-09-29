---
type: feature
stage: implemented
description: The git-new-branch skill starts every work branch at the freshly fetched remote base with its own upstream, and git-commit plus a pre-commit hook keep commits off the default branch.
generated:
  by: claude-code/opus-5.5
  at: 2026-09-29T12:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/git-new-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/git-commit/SKILL.md
- resource: .pre-commit-config.yaml
---

# git-new-branch

## Purpose

Skills that need a work branch — `pr-open`, `update-branch`, `iwe-implement` —
route its creation through one skill instead of an ad-hoc `git checkout -b`,
which branches from whatever is checked out. A branch that tracks the base
instead of its own upstream is refused by `pr-open`, so the branch is pushed
with its own upstream the moment it exists.

## Behaviour

**`/agentdev:git-new-branch <name>`** fetches the remote, creates the branch at
the fetched base without tracking it, and pushes it at once so it tracks
`<remote>/<name>`. It refuses a name that exists locally or on the remote,
carries uncommitted changes when Git can, and stashes only after the user
approves. `--worktree` creates the branch in a new worktree and leaves the
current checkout alone. Commits made on `main` or `master` move onto the new
branch, and the base is then merged in through `/agentdev:update-branch`.

**Commits stay off the default branch.** `/agentdev:git-commit` commits only
through a script that refuses the default branch and a detached `HEAD`, and this
repository's pre-commit configuration rejects a direct `git commit` on `main` or
`master`.

**Implement starts on a work branch.** `/agentdev:iwe-implement` creates the
branch, named from the plan slug, when it starts on `main` or `master`.

The contract is [git-new-branch](../spec/git-new-branch.md).

## Edge cases

- **The remote has no `main`.** The base falls back to the remote's default
  branch, through `refs/remotes/<remote>/HEAD` or `gh repo view`.
- **The push fails.** The local branch is kept and the failure reported; no ref
  is updated through an API.
- **The stash pops with conflicts.** They are resolved through
  `/agentdev:git-merge-resolve`, and the stash entry is dropped only afterwards.

## Open questions

None — every design question this feature raised is settled.

## References

- Plan: [git-new-branch skill](../plans/20260928-git-new-branch-skill.md)
