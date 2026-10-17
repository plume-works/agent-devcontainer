---
type: feature
stage: implemented
description: update-branch brings in the commits the branch's own upstream gained on the remote — fast-forward or merge — before it merges the base, so the update pushes without a second merge.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-16T12:00:00Z
sources:
- resource: docs/knowledge/data/plans/20261012-update-branch-pulls-upstream.md
- resource: .agents/plugins/agentdev/skills/update-branch/agent-code/update-branch.sh
---

# update-branch pulls the branch's upstream

## Purpose

A remote branch can hold commits the local one lacks — pushed from another
checkout, an autofix bot, or GitHub's "Update branch" button. Merging the base
onto the stale local branch produced a push the remote refused, and a second
merge that could bring resolved conflicts back.

## Behaviour

**`/agentdev:update-branch`** syncs the branch with its configured upstream
between the fetch and the base merge, and reports what it did as
`UPSTREAM_ACTION`: `none` when the branch already contains it, `fast-forward`
when the branch was only behind, `merge` when the two diverged, `untracked` with
no upstream, `base` when the upstream is the base ref, and `gone` when the
remote branch no longer exists. The up-to-date check then compares the base
against the synced branch.

The contract is [update-branch](../spec/update-branch.md).

## Edge cases

- **Either merge conflicts.** The run stops with `MERGE_CONFLICTS`, `SOURCE`
  naming the merge; after the resolution is committed, a rerun continues to the
  next merge.
- **The upstream is gone.** A warning is printed and the base merge proceeds;
  the push recreates the remote branch.
- **Only a fast-forward happened.** The run still reports `ALREADY_UP_TO_DATE`
  when the base needed no merge.

## Open questions

None — the design is settled.

## References

- Plan: [update-branch pulls its
  upstream](../plans/20261012-update-branch-pulls-upstream.md)
