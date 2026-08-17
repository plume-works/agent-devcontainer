---
type: task
created: 2026-08-17
stage: planned
priority: high
description: Tighten the ai-review-present gate so it requires a review of the current head SHA and stops accepting weak signals, closing the gap that lets unreviewed code merge behind a green required check.
generated:
  by: claude-code/opus-5
  at: 2026-08-17T09:00:00Z
sources:
- resource: .github/workflows/require-ai-review.yml
- resource: docs/knowledge/data/plans/20260816-ai-responder-workflows.md
- resource: https://github.com/plume-works/agent-devcontainer/pull/65#discussion_r3794958400
---

# Tighten the ai-review-present gate

`require-ai-review.yml` was imported verbatim by
[AI responder workflows](../plans/20260816-ai-responder-workflows.md), which
recorded the gate's permissive acceptance rules under `## Out of scope`:
changing them during an import would conflate porting upstream with improving
it. That boundary was right, and this is the follow-up it named.

Two independent weaknesses let the gate report green over code no AI has read.

## Commit staleness

The gate never compares a review against the PR's current head. `commit_id` is
read only to build log strings (`require-ai-review.yml:107`, `:124`, `:136`);
`head.sha` and `head_sha` appear nowhere in the script. The workflow does re-run
on `synchronize`, but on that event `context.payload.review` is undefined, so it
falls through to the `listReviews()` polling loop (`:156`, `:192`), which
returns every historical review regardless of the commit it addressed.

So one review followed by any number of pushes keeps the check green. The `+1`
reaction path is worse: `reactions.listForIssue` carries no commit association
at all, so a reaction can never be invalidated by a later push.

This is not theoretical — it was reproduced on PR #65 during the import. The
gate reported `pass` while the only qualifying review predated several pushes,
and at another point passed on a *human* review, because `commented` is in
`acceptedReviewStates`.

## Permissive acceptance

The original out-of-scope note: the `+1`-reaction path and the `commented` state
are weak enough that nearly any bot comment satisfies the check.

## What to do

- Compare each candidate review's `commit_id` against the PR head SHA and accept
  only a review of the current head.
- Decide what the reaction path means once staleness is enforced. A reaction
  cannot be tied to a commit, so it either goes or becomes explicitly
  best-effort — it cannot be both permanent and a merge gate.
- Revisit `commented` in `acceptedReviewStates`, which is what lets a human
  comment satisfy a check named for AI review.
- Re-check the fix against a PR that pushes new commits after a review lands:
  the gate must go red until the responder reviews the new head.

## Sequencing

[AI responder workflows](../plans/20260816-ai-responder-workflows.md) Task 6
ends by adding `ai-review-present` to branch protection. Making it required
while it can be satisfied by a stale review would give the repository a merge
gate that does not gate — worse than no check, because it reads as assurance.
Either tighten this first, or make it required knowing it is advisory until
then. That call belongs to the maintainer.
