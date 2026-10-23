---
type: bug
description: Pushing new work to an already-reviewed pull request through pr-sync, pr-open's update mode, or pr-merge's CI-fix push never evaluates whether a fresh AI review is needed, and the once-per-head trigger rule lives only in conversation memory.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-23T12:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-sync/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md
- resource: docs/knowledge/data/spec/ai-review-gate.md
---

# Bug: PR updates skip the re-review evaluation

## Symptom

The [AI review gate](../spec/ai-review-gate.md) keeps passing on an existing
review after later pushes, and leaves refreshing the review to the author.
`pr-eval-review-needed` is the skill that makes that call, but the push paths
that update a reviewed pull request never invoke it: `pr-sync` and `pr-open` in
update mode end after `gh pr edit`, and `pr-merge` restarts its loop after a
CI-fix push. Behavior no reviewer has seen can merge behind a green gate.

When a review is requested, nothing durable enforces the once-per-head-SHA rule:
`pr-request-ai-review` states it as prose, and `pr-merge`'s AI Review Recovery
keeps its ledger in the conversation, so a second session on the same head posts
a second trigger and starts a second review run.

## Reproduction

1. On a pull request with an accepted AI review, commit new runtime behavior
   that no review thread asked for.
2. Run `/agentdev:pr-sync`.
3. `pr-open` detects update mode, pushes, edits the title and body, and stops.
   No re-review decision is reported and no review is requested.

## Root cause

`pr-eval-review-needed` has a single caller, `pr-feedback-resolution`'s Final
Verification workflow. `pr-open`'s update mode and `pr-merge`'s CI-fix step push
to reviewed pull requests without reaching it.

The eval's test asks "did I change anything the reviewer did not direct?" — a
question only a session that just resolved feedback can answer. A cold run from
`pr-sync` or `pr-merge` has no evidence source for what was directed.

A trigger comment records no head SHA, so "already requested for this head" can
only be remembered, not read back from the pull request.

## Fix

Open. Planned in [PR updates re-evaluate the AI
review](../plans/20261023-pr-update-reevaluates-review.md).

## Key references

Verified anchor points (line numbers as of 2026-10-23):

- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:266` — step 9, create or
  update the pull request; update mode ends here
- `.agents/plugins/agentdev/skills/pr-sync/SKILL.md:8` — delegates to pr-open
  update mode
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:199` — step 5, CI-fix
  commit and push
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:259` — AI Review Recovery's
  in-conversation per-head-SHA trigger ledger
- `.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md:338` — the
  eval's only caller
- `.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md:31` — the
  session-relative test
- `.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md:67` — "Post at
  most once per head SHA", prose only
