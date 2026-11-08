---
type: architecture
description: AI reviews are requested with a one-shot request-ai-review label and suppressed with a standing skip-ai-review label; assignment, reviewer requests, the body markers, and requested effort tiers no longer start or shape a review. Supersedes assignee-triggered re-reviews and PR review effort tiers.
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
  on the pull request from the moment someone adds it until a review starts for
  it, and the review job removes it as `plume-works-quill` before Claude runs;
- `assigned` no longer requests a review, so an assignee means ownership only;
- `review_requested` and `review_request_removed` are no longer triggers;
- a `skip-ai-review` label replaces the `[ci:skip-ai-review]` body marker; it
  stays until someone removes it and suppresses only the automatic reviews on
  open, ready for review, reopen, and push; an explicit `request-ai-review`
  always runs a review;
- the `[ci:review-effort=light|full]` marker and requested effort tiers are
  removed; every review sizes itself;
- every run in the pull request's `pr-<n>` concurrency group takes a
  `request-ai-review` it finds, and `request-review.py` re-sends a label that no
  unfinished run is left to take; a request on a draft or from someone without
  write access stays until a later run reviews it.

A `skip-ai-review` label saves the review runs that would fail while Claude is
unavailable. It does not let a pull request merge without ruleset bypass,
because `ai-review-present` still requires an accepted review.

## Approach

```
 add request-ai-review ──► pull_request/labeled ──► concurrency pr-<n>
                                                     │
 add any other label ────► pull_request/labeled ──► concurrency label-<run id>
                                                     │
  preflight ── reads current labels from the API (GITHUB_TOKEN, read-only)
          ├── wantsReview: request-ai-review in pr-<n>  → yes (skip label ignored)
          │                opened/ready/reopened/push*   → yes unless skip-ai-review
          │                anything else                 → no
          ▼
  claude-respond (if wantsReview) ── mint App token ── removes request-ai-review
          └── Claude review ──► ai-review-present (every run, never skipped)

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
- Preflight reads the pull request's labels from the API, so a `skip-ai-review`
  added just after creation still counts when it lands before preflight reads
  it.
- Every run in `pr-<n>` takes a `request-ai-review` it finds: preflight reviews
  when it is present, and `run-claude-responder` removes it with the minted App
  token right before the Claude step, so the timeline shows `plume-works-quill`
  removing it. A run that does not review leaves the label for a later run: on a
  draft, it waits for ready for review; from someone without write access, it
  waits for a writer's run. A request whose own run was cancelled while pending,
  because a later event replaced it in `pr-<n>`, is taken by the replacing run.
  A run started by another label leaves the label in place.
- `request-review.py` requests a review by adding `request-ai-review`. Finding
  the label already present, it reports `ALREADY_REQUESTED` while a run of
  `ai-responder.yml` on the head branch is unfinished, and otherwise removes and
  re-adds it, firing a new `labeled` event. A person re-adding a label already
  present sends nothing, because GitHub fires no event for it.
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
- A request run cancelled, or failing, before its review job removes the label
  leaves `request-ai-review` on the pull request until the next run in `pr-<n>`
  takes it or `request-review.py` re-sends it.
- A request from someone without write access stays on the pull request, and the
  next run a writer starts in `pr-<n>` reviews it.
- An unfinished run started by another label also makes `request-review.py`
  report `ALREADY_REQUESTED`; the next call after it finishes re-sends the
  label.

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
