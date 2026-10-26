---
type: architecture
description: AI re-reviews are requested by assigning the pull request, because only a pull_request-event run's ai-review-present is counted by the PR rollup and the main ruleset; the @claude review comment trigger and Codex review acceptance are dropped.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-26T04:00:00Z
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/ai-review-status/action.yml
- resource: docs/knowledge/data/spec/ai-review-gate.md
- resource: https://github.com/plume-works/agent-devcontainer/pull/472
- resource: https://github.com/plume-works/agent-devcontainer/pull/475
---

# Assignee-triggered AI re-reviews

## Decision

The maintainer decided on 2026-10-26 to:

- request a re-review by assigning the pull request, re-triggering by removing
  the assignee and adding them back;
- drop the `@claude review` comment trigger;
- drop Codex reviews, and the Codex `+1` reaction, from the AI review gate.

Dropping the free-form `@claude <prompt>` task trigger is separate,
lower-priority work: [Drop the `@claude <custom prompt>` free-form task
trigger](../backlog/drop-claude-free-form-task-trigger.md).

## Which runs the gate is counted from

The `main` ruleset requires `ai-review-present` from GitHub Actions, matched by
name on the head commit. Merge state, the pull request's status rollup, and
`gh pr checks` all draw on the same set of check suites:

- **Counted:** suites created by the pull request's own events — `pull_request`
  (including `assigned` and `synchronize`) and `pull_request_review`.
- **Not counted:** a `workflow_dispatch` run on the head branch. That holds even
  though its suite lists the pull request, its check runs land on the head
  commit, and they carry the required name and app. It is the defect in [Bug: a
  comment-requested review's gate does not count toward
  merge](../bugs/dispatched-review-gate-not-counted.md). The dispatch design it
  replaces is recorded in [Dispatched review
  identity](dispatched-review-identity.md).
- The gate's `needs: claude-respond` coupling holds only inside one run. A
  review in one run is never awaited by a gate in another.
- A review posted with `GITHUB_TOKEN` raises no `pull_request_review` event, so
  publishing a review never re-runs a gate by itself.

## Behaviour of the assignee trigger

- **Adding an assignee** fires `pull_request`/`assigned`. Preflight's
  `wantsReview` is true for `assigned` whether or not an accepted review exists,
  so the run reviews the head, and its gate is counted.
- **Merge is held during a re-review.** On a head whose earlier gate passed, the
  merge state read `BLOCKED` from the moment the assigned run started until its
  gate passed, even though the earlier gate's success stayed in the rollup. Two
  things are unverified: whether that hold comes from the required check being
  re-expected or from the pending non-required review check, and whether
  auto-merge waits. Both are tracked in [Verify that auto-merge waits for an
  assignee-triggered review](../backlog/verify-assignee-review-automerge.md).
- **Removing an assignee** starts no run, because `unassigned` is not a trigger
  type. Adding a user who is already assigned fires no event, so a re-trigger is
  remove, then add.
- **Authorization** is preflight's write-access check on `context.actor`, the
  person who assigned. Assigning already needs triage access or higher.
- **The skip marker wins.** `[ci:skip-ai-review]` is evaluated before the
  `assigned` rule, so assigning a marked pull request runs the gate without a
  review.
- **Bot-authored and fork pull requests** are excluded at preflight's `if:`, as
  for every `pull_request` event.
- **A queued review can be dropped.** All `pull_request` events for one pull
  request share the concurrency group `pr-<n>`, which cancels in progress only
  on `synchronize`. GitHub keeps one running and one pending run per group, and
  a newer pending run replaces an older one. An assigned run waiting behind
  another run of the group is therefore dropped, without notice, by a later
  `review_requested`, `ready_for_review`, or `assigned` event.

## Rejected alternatives

- **Keep the `@claude review` comment trigger.** Its dispatched gate is not
  counted, so it neither holds a merge nor clears a red gate.
- **Re-run the gate by re-requesting a reviewer.** `review_requested` re-runs
  the gate in a counted run without a second review, but it needs a second
  collaborator. An author cannot be requested as their own reviewer, and the
  request leaves visible reviewer churn on the pull request.
- **Have the dispatched run re-run the latest `pull_request` run** of the
  workflow. That keeps the comment trigger at the cost of a second run per
  review, and the gate is still not pending while the dispatched review runs.
- **Post the review under an identity whose review raises a
  `pull_request_review` event.** That needs a separate app identity and
  credential for the responder, and it only re-runs the gate after the review,
  not while it runs.

## Key references

Verified anchor points (line numbers as of 2026-10-26):

- `.github/workflows/ai-responder.yml:74` — concurrency group, cancelling only
  on `synchronize`
- `.github/workflows/ai-responder.yml:269` — the skip marker, checked before the
  action rules
- `.github/workflows/ai-responder.yml:275` — `assigned` among the actions that
  always review
- `.github/workflows/ai-responder.yml:509` — `ai-review-present`, needing
  `claude-respond`
- `.github/actions/ai-review-status/action.yml:68` — Codex logins accepted by
  the gate
