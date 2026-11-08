---
type: architecture
description: AI reviews are requested with a one-shot request-ai-review label and suppressed with a standing skip-ai-review label; assignment, reviewer requests, the body markers, and requested effort tiers no longer start or shape a review. Supersedes assignee-triggered re-reviews and PR review effort tiers.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-08T03:30:00Z
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py
- resource: data/plans/20261108-label-review-triggers.md
---

# Label review triggers

## Context

The maintainer's goal is an easy, trusted, explicit way to request a re-review.

The maintainer decided on 2026-11-08:

- a `request-ai-review` label is the one way to request a review; the label is
  on the pull request only from the moment someone adds it until a run accepts
  or rejects it, and preflight removes it with `GITHUB_TOKEN` when the run
  starts;
- `assigned` no longer requests a review, so an assignee means ownership only;
- `review_requested` and `review_request_removed` are no longer triggers;
- a `skip-ai-review` label replaces the `[ci:skip-ai-review]` body marker; it
  stays until someone removes it and suppresses only the automatic reviews on
  open, ready for review, reopen, and push; an explicit `request-ai-review`
  always runs a review;
- the `[ci:review-effort=light|full]` marker and requested effort tiers are
  removed; every review sizes itself.

A `skip-ai-review` label saves the review runs that would fail while Claude is
unavailable. It does not let a pull request merge without ruleset bypass,
because `ai-review-present` still requires an accepted review.

## Approach

```
 add request-ai-review ──► pull_request/labeled ──► concurrency pr-<n>
                                                     │
 add any other label ────► pull_request/labeled ──► concurrency label-<run id>
                                                     │
 preflight ── removes request-ai-review (GITHUB_TOKEN, issues: write)
          ├── reads current labels from the API
          ├── wantsReview: request-ai-review            → yes (skip label ignored)
          │                opened/ready/reopened/push*   → yes unless skip-ai-review
          │                anything else                 → no
          ▼
 claude-respond (if wantsReview) ──► ai-review-present (every run, never skipped)

 * push only while no accepted review exists
```

- A label fires `pull_request`/`labeled`, a `pull_request` event, so its run is
  counted by the `main` ruleset and the status rollup and its checks land on the
  head commit, as [Assignee-triggered AI re-reviews](assignee-review-trigger.md)
  records for `assigned`.
- `ai-responder.yml`'s `pull_request` types are `opened`, `reopened`,
  `ready_for_review`, `synchronize`, and `labeled`.
- A `labeled` event for any label other than `request-ai-review` takes a
  concurrency group keyed by its run id, so it never replaces a review queued in
  `pr-<n>`.
- `ai-review-present` runs on every event, a label of any name included. A job
  skipped by its own `if:` satisfies a required check, so skipping the gate for
  an unrelated label would let anyone with triage access turn it green.
- Preflight removes `request-ai-review` in its first step, before authorization,
  so a rejected request is cleared too. It reads the pull request's labels from
  the API, so a `skip-ai-review` added just after creation still counts when it
  lands before preflight reads it.
- `request-review.py` requests a review by adding `request-ai-review`, and
  treats the label still being on the pull request as a pending request.
- `pr-review` keeps its internal effort matrix to size a review; nothing
  requests a tier, and `run-claude-responder` has no `model` input.

## Known limits

- A run started by an unrelated label evaluates the gate on the existing
  reviews, so while a requested review is still running, that run's gate can
  report a result the pending review later replaces.
- Preflight does not run on fork or bot-authored pull requests, so a
  `request-ai-review` added there stays until someone removes it; no review can
  run on them either way.
- An `opened` run whose preflight reads the labels before a creation-time
  `skip-ai-review` lands still reviews.

## Rejected alternatives

- **Keep the assignee toggle**: it borrows a field that means ownership, and
  takes two actions per request.
- **A comment trigger**: a comment-started run is not a `pull_request` run, so
  its gate does not count toward merge, and it requires parsing free-form
  comments.
- **A persistent `ai-review-requested` state label removed after the review
  posts**: a failed review leaves the label on, and it must be removed by hand
  before the next request.
- **Labels for the effort tier**: every review sizes itself.
- **A repository-wide review pause**: a per-PR `skip-ai-review` label covers a
  Claude outage, and a pause would still need bypass merges unless it waived the
  gate.

This supersedes [Assignee-triggered AI re-reviews](assignee-review-trigger.md)
and [PR review effort tiers](pr-review-effort-tiers.md).
