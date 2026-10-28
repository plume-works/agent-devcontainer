---
type: architecture
description: How the required ai-review-present check could read pending while a re-review runs, so a merge or auto-merge waits for it; a separate commit status is the leading candidate, and the marker-commit trigger and a merged review-and-gate job are rejected.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-27T18:00:00Z
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/ai-review-status/action.yml
- resource: docs/knowledge/data/spec/ai-review-gate.md
- resource: docs/knowledge/data/architecture/assignee-review-trigger.md
- resource: docs/knowledge/data/backlog/verify-assignee-review-automerge.md
---

# Holding the AI review gate during a re-review

## Question

[Verify that auto-merge waits for an assignee-triggered
review](../backlog/verify-assignee-review-automerge.md) asks why the merge state
reads `BLOCKED` during a re-review, and whether auto-merge waits for it. Behind
it is a design question: how can the required `ai-review-present` check read
pending while a re-review runs, and green again once the review lands?

## What is known

- **During a re-review of an unchanged head, the required check most likely
  keeps reading the earlier pass.** The gate job's check run is created only
  once its `needs: claude-respond` is met, so nothing new named
  `ai-review-present` exists on the head while the review runs. The pull
  request's status rollup listed the earlier run's passing `ai-review-present`
  while a requested review was in progress. The check-run API exposes no
  creation time, so the job's creation point is inferred from its start time.
- **If so, auto-merge would not wait for a re-review.** It waits on required
  checks, which already pass. The `BLOCKED` state then comes from something
  else, most likely the pending `Claude PR Review Responder` check, which is not
  required.
- **A push gives the new head a fast pass on an existing review.** The
  `synchronize` run skips the review on a reviewed pull request, and its gate
  passes in seconds. A re-review requested after the push therefore starts after
  the new head's gate is already green.
- **A required check is evaluated on the head commit**, so every head needs an
  `ai-review-present` of its own. Without the `synchronize` trigger, every push
  would block until a review run reported on the new head. That includes the
  formatter commits `reformat.yml` pushes with `REPO_PAT`, which start runs.
- **Exposure is narrow.** Only Renovate uses auto-merge, and its pull requests
  are trusted-bot pull requests whose review the gate waives. `pr-merge` never
  enables auto-merge, and stacks cannot use it. The exposed case is a person who
  merges, or enables auto-merge, on a green gate before a re-review lands.

## Leading candidate: a separate commit status

The review run publishes `ai-review-present` as a commit status of its own:
`pending` when a run that will review starts, then `success` or `failure` from
the gate's acceptance check. The newest status for a context is the one that
counts, which is exactly the pending-then-green lifecycle wanted.

- Statuses are attached to the commit directly, not to a check suite. The
  failure mode in [Bug: a comment-requested review's gate does not count toward
  merge](../bugs/dispatched-review-gate-not-counted.md) is a check whose suite
  the rollup leaves out, so it does not apply.
- The `main` ruleset requires `ai-review-present` from the GitHub Actions app.
  Whether a status posted with `GITHUB_TOKEN` counts as that source is an open
  question below.
- The gate job must stop using the name `ai-review-present`, so that its own
  check run and the status do not compete for the required name.
- A custom check run through the Checks API is the alternative carrier. It lands
  in a check suite, so it carries the risk the commit status avoids.

The review job and the gate job keep their current shape. The candidate changes
only how the gate's result is published.

## Rejected approaches

- **A marker commit as the re-review request.** The agent would run the
  re-review evaluation before pushing and, when a review is needed, push an
  empty commit carrying `[ci:new-review-required]`; the gate would then refuse
  any review older than the marker. The maintainer rejected it on 2026-10-27 as
  a dead end. Telling whether an existing review covers a marker breaks down:

  - by commit ID, every rebase and stack retarget loses coverage;
  - by fingerprinting what the pull request adds, an empty marker commit has the
    same fingerprint as its parent, so a review of the parent appears to cover
    the marker. The fingerprint also depends on the base at the time of the
    review, which GitHub does not record, so stack rebases lose coverage.
    `git patch-id --stable` ignores whitespace, which changes meaning in Python
    and YAML, and its hunks vary with rename detection and the diff algorithm;
  - by matching markers on author, author date and message across rewrites,
    coverage survives a rebase but is lost whenever any of the three changes,
    and the gate has to carry its own history-matching rule.

  Every variant also moves the re-review decision before the push and adds a
  commit to the pull request for each request.

- **Merging the review and the gate into one job.** The required check would go
  pending as soon as a review run starts. The maintainer decided on 2026-10-27
  to keep the jobs as they are. Merged, every gate-only run would also pull the
  review container, take the `claude-review` environment, and hold the review's
  write permissions, and `request-review.sh` could no longer tell a reviewing
  run from a gate-only one by check name.

- **Deleting or rewriting the earlier passing check.** GitHub has no API to
  delete a check run, and newer results with the same name already take
  precedence, so the earlier pass never needs clearing.

## Open questions

- Does a commit status posted with `GITHUB_TOKEN` satisfy the ruleset's
  requirement for `ai-review-present` from the GitHub Actions app?
- When a passing check run and a newer pending status share the name
  `ai-review-present`, which one does the ruleset read? The answer decides
  whether the gate job can be renamed in a later step, or has to be renamed in
  the same change.
- Does auto-merge wait while the status is `pending`?
- A review run that is cancelled leaves `pending` behind until the next run.
  That fails closed. Is that acceptable?
- Does a push to a reviewed pull request need closing too, or is a re-review of
  an unchanged head enough? Options weighed: accept the gap; keep the
  `synchronize` run but publish `pending` until a review or an explicit "no
  re-review needed" releases it; drop `synchronize`; review every push.
- The gate accepts any review by `claude[bot]` or `github-actions[bot]`, so a
  free-form `@claude` task, or any same-repository workflow with
  `pull-requests: write`, can produce one. Should acceptance be restricted to
  reviews the review job produced?
- All `pull_request` events share one concurrency group, and a newer queued run
  replaces an older one. Should preflight decide to review from the pull
  request's state on any event, rather than from the triggering action, so a
  dropped run cannot leave the gate red with nothing reviewing?

## What would settle it

A spike on throwaway pull requests into a scratch branch that carries a
temporary ruleset requiring `ai-review-present`: post `pending` and then
`success` statuses from the pull request's workflow, enable auto-merge, and read
the merge state and whether the pull request merges at each step. Closing this
finding means either a plan for the commit status, or a recorded decision that
the narrow exposure is not worth the change.
