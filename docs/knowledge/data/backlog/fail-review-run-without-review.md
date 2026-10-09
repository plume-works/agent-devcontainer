---
type: task
created: 2026-10-08
stage: planned
priority: medium
description: Fail a Claude PR review responder run that published no review of its own, by tying the published review to the run through an identity rather than a time window.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-08T00:00:00Z
sources:
- resource: .github/actions/run-claude-responder/action.yml
- resource: .github/workflows/ai-responder.yml
- resource: https://github.com/plume-works/agent-devcontainer/issues/198
---

# Fail a review run that published no review

A `Claude PR Review Responder` job can finish green without publishing a review,
and `ai-review-present` passes it on an earlier review: the gate asserts that
the pull request was reviewed, not that this run reviewed it. That property is
deliberate — see [AI review gate](../spec/ai-review-gate.md) — so the run itself
must fail when it published nothing, or a re-review that vanishes stays silent.

The known cause of such runs is closed in [The review orchestrator ends its turn
while its passes are still
running](../bugs/review-orchestrator-ends-turn-while-passes-run.md); this check
is the safety net for any cause that is not.

## What to do

The check needs an identity, not a window. A time-window predicate — a timestamp
stamped before the Claude step, then any review by `claude[bot]` or
`github-actions[bot]` submitted after it — is unsound: nothing ties the matched
review to the run being checked, so an abandoned run passes on a concurrent
run's review.

Concurrent responder runs on one pull request are ordinary. A dispatched run's
concurrency group is `dispatch-<comment_id>`, so two `@claude review` comments
occupy different groups, and a dispatched run and a `pull_request` run
(`pr-<n>`) are distinct too. `cancel-in-progress` is set only for a
`pull_request` `synchronize` event, so nothing cancels an in-flight dispatched
run.

Candidate identities:

- the run URL stamped into the published review body, matched after the session
  ends;
- the submitted review's id captured from the session's output.

Done when a responder run whose session published no review fails the job, and a
concurrent run's review cannot satisfy that check.

## Key references

Verified anchor points (line numbers as of 2026-10-08):

- `.github/workflows/ai-responder.yml:74` — `concurrency`, the per-comment and
  per-PR groups, with `cancel-in-progress` at line 82
- `.github/workflows/ai-responder.yml:509` — `ai-review-present`, the gate that
  accepts an earlier review
