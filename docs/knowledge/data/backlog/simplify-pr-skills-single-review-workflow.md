---
type: task
description: Once comment-requested reviews run on the PR head branch, retire the run-discovery and polling prose in the pr-* skills that exists only because those runs were filed against main.
stage: planned
priority: medium
created: 2026-09-03
generated:
  by: claude-code/fable-5-1
  at: 2026-09-03T01:30:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-discover-ai-responder/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md
---

# Simplify the pr-* skills for the single review workflow

[One AI review workflow with a needs-coupled gate](../plans/20260903-single-ai-review-workflow.md)
makes a comment-requested review a `workflow_dispatch` run on the pull request's
head branch. Its check then appears in `gh pr checks` on the head SHA, and the
gate is pending for the whole review.

Three skills carry logic that exists only because that was not true:

- `pr-discover-ai-responder` greps run logs for `Determine checkout ref` to tell
  which PR a `main`-filed run belongs to.
- `pr-merge`'s AI Review Recovery keeps a per-SHA trigger ledger and watches
  responder runs by id because `gh pr checks` could not see them.
- `pr-request-ai-review`'s "Confirm it started" section explains why the run is
  not attached to the head.

The skills are consumed by other repositories too, some still on the
two-workflow shape (`claude-review.yml` is named in the discovery skill), so the
simplification has to either detect which shape a repository runs or wait until
every consumer has moved. Decide at planning time; keep "post at most once per
head SHA" in either case.
