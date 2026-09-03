---
type: spec
description: How the required AI review gate accepts a review and when the responder is allowed to act on a pull request.
generated:
  by: codex/gpt-5
  at: 2026-09-03T18:51:21Z
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/ai-review-status/action.yml
- resource: .github/actions/run-claude-responder/action.yml
---

# AI review gate

## Requirement: PRs are blocked until an AI review exists

A pull request SHALL NOT be mergeable until either Claude or Codex has reviewed
it. The `ai-review-present` check SHALL accept a review from `claude[bot]` or
`github-actions[bot]`, a review from `chatgpt-codex-connector[bot]`, or a `+1`
reaction from `chatgpt-codex-connector[bot]`, in state `approved`,
`changes_requested`, or `commented`.

The check SHALL NOT require that the review name the pull request's current head
commit. It asserts that the pull request has been reviewed, not that each pushed
commit has been: reviewing every commit is prohibitively expensive, and neither
AI nor human reviewers work that way. Refreshing a review is the author's call,
requested with an `@claude review` comment the way a human re-review is
re-requested.

The check SHALL be a job of the same workflow as the review job, depending on
it, so that it is pending for as long as a review of the pull request is running
in that workflow run, and it SHALL evaluate without polling.

### Scenario: a reviewed PR receives a further push

- **WHEN** an accepted AI review exists on the pull request and the author
  pushes a commit after it
- **THEN** the review job is skipped and `ai-review-present` passes on the
  existing review.

### Scenario: an unreviewed PR receives a further push

- **WHEN** no accepted AI review exists on the pull request and the author
  pushes a commit
- **THEN** the review job runs and `ai-review-present` reports its outcome.

### Scenario: Claude reviews a PR through the responder workflow

- **WHEN** the review job in a run posts a review on a pull request
- **THEN** `ai-review-present` in that run passes once the job completes, and is
  pending until then.

### Scenario: the review job fails

- **WHEN** the review job in a run fails or is cancelled
- **THEN** `ai-review-present` in that run fails.

### Scenario: Codex reviews a PR through Codex web

- **WHEN** a maintainer runs a Codex review outside GitHub Actions and it posts
  as `chatgpt-codex-connector[bot]`
- **THEN** the review event re-runs the workflow and `ai-review-present` passes.

### Scenario: no AI has reviewed

- **WHEN** the review job did not run in a run and no accepted review exists on
  the pull request
- **THEN** `ai-review-present` fails, blocking merge.

## Requirement: the responder only acts for authorized same-repository requests

The responder SHALL NOT check out or execute code for a pull request originating
from a fork, and SHALL NOT act on a request from an actor without write access.
Both gates SHALL apply before a dispatch is issued for a comment and again in
the dispatched run.

The PR review responder SHALL run with read-only repository contents access.
Free-form task requests that may edit repository contents SHALL run in a
separate job with write repository contents access.

### Scenario: a fork PR triggers the responder

- **WHEN** the pull request head repository differs from the workflow repository
- **THEN** preflight records the fork, no dispatch is issued, and every
  responder job is skipped before any checkout.

### Scenario: a user without write access mentions @claude

- **WHEN** the requesting actor's permission is not `admin`, `maintain`, or
  `write`
- **THEN** preflight fails, no dispatch is issued, and no responder job runs.

## Requirement: a review runs on first push and on explicit request

The review job SHALL run when a pull request is opened, marked ready for review,
reopened, or assigned; when a `workflow_dispatch` requests it; and on a push to
a pull request that has no accepted review. It SHALL NOT run for a
`pull_request` event on a draft pull request.

### Scenario: a draft is opened

- **WHEN** a pull request is opened as a draft
- **THEN** no review runs until the pull request is marked ready for review.

## Requirement: comment mentions run the pull request branch's workflow

A `@claude` mention opening a comment, review, or review comment on a pull
request SHALL be answered by a `workflow_dispatch` of this workflow on the pull
request's head branch, so the run executes the branch's own workflow file and
its checks attach to the head commit. The dispatched responder run SHALL append
its run link to the requesting comment, review, or review comment before Claude
starts.

### Scenario: a maintainer comments `@claude review`

- **WHEN** a writer opens a pull request comment with `@claude review`
- **THEN** a run of this workflow starts on the head branch, reviews the pull
  request, and appends its run link to the comment.

### Scenario: the head branch has no workflow file

- **WHEN** the pull request's head branch does not carry `ai-responder.yml`
- **THEN** the bridge fails naming the branch, and no review runs.
