---
type: task
created: 2026-10-20
stage: planned
priority: low
description: Plan the post-merge local cleanup for pr-merge-stack, which lands several layers with one gh stack merge.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-20T00:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-merge-stack/SKILL.md
- resource: .agents/plugins/agentdev/skills/gh-stack/SKILL.md
rank: 2200
---

# Clean up the local checkout after pr-merge-stack

[Clean up the local checkout after pr-merge](pr-merge-post-merge-cleanup.md)
covers one merged head branch. A stack lands every layer with one
`gh stack merge`, so the cleanup has to settle what a single head does not:
which layers' local branches to release, which plan or plans decide the next
branch when layers serve different plans, and how the release interacts with the
stack metadata `gh stack` keeps — see [Stacked PRs](../spec/stacked-prs.md).

Plan it once the single-PR cleanup has shipped and its script can be reused.
