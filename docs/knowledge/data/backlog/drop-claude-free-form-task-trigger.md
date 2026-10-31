---
type: task
stage: planned
priority: low
created: 2026-10-26
description: Remove the free-form `@claude <prompt>` task responder — the comment, review, and issue mentions that dispatch a Claude task — once review re-requests move to the assignee trigger.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-26T03:30:00Z
sources:
- resource: .github/workflows/ai-responder.yml
- resource: docs/knowledge/data/spec/ai-review-gate.md
rank: 2300
---

# Drop the `@claude <custom prompt>` free-form task trigger

Retire the free-form task path in `.github/workflows/ai-responder.yml`:

- the `wantsTask` branch of preflight's "Determine agent prompts" step;
- the `bridge` job's task dispatch for pull request mentions;
- the `issues` opened/assigned mention trigger;
- the `claude-task` responder job;
- the `task` input of `workflow_dispatch`.

Then update [spec/ai-review-gate](../spec/ai-review-gate.md) and the README to
match.

Once `@claude review` is dropped in favour of the assignee trigger, the
free-form task path is the only remaining reason for three pieces of the
responder: comment-mention matching, the bridge from `main` to the head branch,
and the forwarded-requester authorization. Removing it shrinks the responder's
untrusted-input surface.
