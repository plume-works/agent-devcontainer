---
type: task
stage: planned
priority: medium
created: 2026-10-26
description: Settle, on two throwaway pull requests, whether an assignee-triggered re-review holds a merge because the required ai-review-present is re-expected, and whether auto-merge waits for it.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-26T04:10:00Z
sources:
- resource: docs/knowledge/data/architecture/assignee-review-trigger.md
- resource: .github/workflows/ai-responder.yml
- resource: https://github.com/plume-works/agent-devcontainer/pull/475
rank: 1300
---

# Verify that auto-merge waits for an assignee-triggered review

[Assignee-triggered AI re-reviews](../architecture/assignee-review-trigger.md)
records that the merge state reads `BLOCKED` while an assigned re-review runs,
but not why, and auto-merge has not been exercised. The plan that adopts the
assignee trigger must not claim auto-merge waits until these two tests settle
it.

1. **What causes `BLOCKED`.** On a `CLEAN` throwaway pull request, re-run one
   non-required job of its latest `pull_request` run, and read
   `mergeStateStatus` while that job is pending. If it reads `BLOCKED`, a
   pending non-required check blocks on its own, and the earlier observation
   does not show the required gate being re-expected.

2. **Whether auto-merge waits.** Use two throwaway pull requests, so nothing can
   land on `main`:

   - PR A goes from scratch branch A into `main`, and is never merged.
   - PR B goes from scratch branch B into branch A.
   - A temporary ruleset on branch A requires `ai-review-present` from GitHub
     Actions.

   Once B is `CLEAN` after its first review, enable squash auto-merge on B. Then
   remove the author as assignee and add them back. Record whether B merges
   before the assigned run's `ai-review-present` completes.

Cleanup removes the temporary ruleset, closes both pull requests, and deletes
both branches.
