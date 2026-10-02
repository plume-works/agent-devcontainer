---
type: task
description: Make pr-feedback-resolution detect a pull request's merge conflicts before any other work and resolve them through update-branch against the PR's own base branch.
stage: done
priority: medium
created: 2026-10-02
completed: 2026-10-02
generated:
  by: claude-code/opus-5-5
  at: 2026-10-02T14:10:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md
- resource: .agents/plugins/agentdev/skills/update-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md
---

# Resolve merge conflicts in pr-feedback-resolution

`pr-feedback-resolution` collects review threads, review bodies, CI, CodeQL, and
Codecov, but never reads the pull request's merge state. A PR that conflicts
with its base gets no `pull_request` workflow runs, so the CI picture the skill
diagnoses is missing or stale until the conflict is resolved.

## What to do

Add a first step to Workflow 1, before any edits:

1. Read `gh pr view <pr> --json mergeable,mergeStateStatus,baseRefName`.
2. On `mergeable: CONFLICTING` or `mergeStateStatus: DIRTY`, invoke
   `/agentdev:update-branch` with `--base <baseRefName>` and follow its
   `git-merge-resolve` handoff for the conflicts. Use the PR's base, not the
   `main` default, so stacked PRs merge their real base.
3. On `UNKNOWN`, GitHub has not computed mergeability yet; re-poll before
   deciding.
4. Otherwise continue with feedback collection.

Running it first also satisfies `update-branch`'s clean-working-tree
precondition, since no feedback edits exist yet.

Scope is conflicts only: `BEHIND` (a strict up-to-date branch rule) does not
trigger the update. Whether the merge warrants a fresh AI review is already
decided by `pr-eval-review-needed` (a clean base merge does not; a judgment-call
conflict resolution does).

This edits skill instructions only — a non-executable artifact — so validate
with the skill validation, not TDD.
