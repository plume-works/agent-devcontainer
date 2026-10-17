---
type: feature
stage: implemented
description: pr-feedback-resolution resolves a pull request's merge conflict with its base before any feedback edit, and pr-merge routes a conflicted PR there, so CI runs on the merged head.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-16T12:00:00Z
sources:
- resource: docs/knowledge/data/plans/20261002-pr-feedback-resolve-merge-conflicts.md
- resource: .agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
---

# PR feedback resolution resolves merge conflicts

## Purpose

A pull request that conflicts with its base gets no `pull_request` workflow
runs, so the CI picture feedback resolution diagnoses is missing or stale until
the conflict is gone.

## Behaviour

**Conflicts first.** `/agentdev:pr-feedback-resolution` reads the PR's merge
state before any feedback edit. A conflicting PR is updated with
`/agentdev:update-branch --base <baseRefName>`, its conflicts resolved, and the
merge pushed, so CI starts on the merged head.

**pr-merge routes conflicts.** `/agentdev:pr-merge`'s monitoring loop sends a
conflicting PR to that step and restarts at its refresh.

The contract is [PR merge conflicts](../spec/pr-merge-conflicts.md).

## Edge cases

- **Mergeability not computed yet.** Both skills re-poll in bounded waits before
  deciding.
- **A PR on another base.** The PR's own base branch is merged, not `main`.
- **A stacked PR.** It is rebased with `gh stack` instead.

## Open questions

None — the design is settled.

## References

- Plan: [Resolve merge conflicts in
  pr-feedback-resolution](../plans/20261002-pr-feedback-resolve-merge-conflicts.md)
