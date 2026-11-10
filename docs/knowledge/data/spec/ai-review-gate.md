---
type: spec
description: How the required AI review gate accepts a review and when the responder is allowed to act on a pull request.
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/ai-review-status/action.yml
- resource: .github/actions/run-claude-responder/action.yml
- resource: openspec/specs/ai-review-gate/spec.md
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: data/plans/20261030-ai-review-verdicts-and-bot-approval.md
- resource: data/plans/20261107-drop-claude-task-responder.md
- resource: data/plans/20261030-responder-quill-app-identity.md
- resource: data/plans/20261108-label-review-triggers.md
---

# AI review gate

## Requirement: PRs are blocked until an AI review exists

A pull request SHALL NOT be mergeable until Claude has reviewed it. The
`ai-review-present` check SHALL accept a review only from
`plume-works-quill[bot]`, in state `approved`, `changes_requested`, or
`commented`.

The check SHALL NOT require that the review name the pull request's current head
commit. It asserts that the pull request has been reviewed, not that each pushed
commit has been: reviewing every commit is prohibitively expensive, and neither
AI nor human reviewers work that way. Refreshing a review is the author's call,
requested by adding the `request-ai-review` label.

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

### Scenario: no AI has reviewed

- **WHEN** the review job did not run in a run and no accepted review exists on
  the pull request
- **THEN** `ai-review-present` fails, blocking merge.

### Scenario: only another identity has reviewed

- **WHEN** the pull request's only reviews are by `github-actions[bot]` or
  `claude[bot]`
- **THEN** `ai-review-present` treats it as unreviewed.

## Requirement: the responder acts as its own GitHub App

The review responder and the trusted-bot approval SHALL post with an
installation token of the `plume-works-quill` App, minted per job with only the
permissions that job needs and after any code from the pull request head has
run. A job whose App secrets are missing SHALL fail and SHALL NOT fall back to
`GITHUB_TOKEN`. The App's token SHALL NOT carry contents write access, and the
responder SHALL NOT open a pull request.

### Scenario: the App secrets are missing

- **WHEN** a responder job runs and `QUILL_APP_CLIENT_ID` or
  `QUILL_APP_PRIVATE_KEY` is empty
- **THEN** the job fails naming the missing secret, and nothing is posted.

## Requirement: the responder only acts for authorized same-repository requests

The responder SHALL NOT check out or execute code for a pull request originating
from a fork, and SHALL NOT act for an actor without write access. The PR review
responder SHALL run with read-only repository contents access, and no responder
job SHALL hold write repository contents access.

### Scenario: a fork PR triggers the responder

- **WHEN** the pull request head repository differs from the workflow repository
- **THEN** preflight is skipped, and every responder job is skipped before any
  checkout.

### Scenario: a user without write access triggers the responder

- **WHEN** the actor of a `pull_request` event has a permission other than
  `admin`, `maintain`, or `write`
- **THEN** preflight fails and no responder job runs.

## Requirement: a review runs on first push and on explicit request

The review job SHALL run when a pull request is opened, marked ready for review,
or reopened, on a push to a pull request that has no accepted review, and when
the `request-ai-review` label is added. The label SHALL run a review whether or
not an accepted review exists. Every run in the pull request's concurrency group
SHALL take a `request-ai-review` it finds on the pull request: the run SHALL
review when the request is authorized and the pull request is not a draft, and
while the pull request carries no `block-ai-reviews`, and the review job SHALL
remove the label with the reviewer App's token once the review finishes, whether
it succeeded or failed, and SHALL NOT remove it when the review is cancelled. A
request whose own run was cancelled while pending is therefore taken by the run
that replaced it. A run that does not review SHALL leave the label for a later
run in that group, as SHALL a run started by another label. A cancelled review
therefore leaves the label until the next run in that group takes it, or until
`request-review.py` re-sends it. An assignment, a reviewer request, and a
reviewer request's removal SHALL NOT start a run. The review job SHALL NOT run
for a `pull_request` event on a draft pull request.

Removing `block-ai-reviews` SHALL start a run in the pull request's concurrency
group, which takes a waiting `request-ai-review`. Every other label event,
adding or removing any other label, SHALL NOT run a review and SHALL NOT share
the pull request's concurrency group, so it never replaces a queued review run.
Preflight does not run on a fork or bot-authored pull request, so a
`request-ai-review` label added there is not removed.

The workflow SHALL be triggered only by pull request, pull request review, and
merge group events: a comment, an issue, or a mention of `@claude` SHALL start
no run, and the workflow SHALL accept no `workflow_dispatch`.

The `ai-review-present` gate SHALL run for every pull request, pull request
review, and merge group event, every label event included.

### Scenario: a draft is opened

- **WHEN** a pull request is opened as a draft
- **THEN** no review runs until the pull request is marked ready for review.

### Scenario: a writer requests a review with the label

- **WHEN** a writer adds `request-ai-review` to a reviewed pull request
- **THEN** a `pull_request` run reviews the pull request, its review job then
  removes the label as `plume-works-quill`, and its `ai-review-present` reports
  that review.

### Scenario: a push replaces a pending request

- **WHEN** `request-ai-review` is added while another run of the pull request is
  in progress, and a push queues before the request's run starts
- **THEN** the push's run reviews the pull request, its review job removing the
  label.

### Scenario: a push lands during a requested review

- **WHEN** a push cancels a review that `request-ai-review` started
- **THEN** the label stays, and the push's run reviews the new head and removes
  it.

### Scenario: a user without write access adds the label

- **WHEN** a user with triage but not write access adds `request-ai-review`
- **THEN** preflight fails, no review runs, and the label stays until a run a
  writer starts reviews the pull request.

### Scenario: a writer assigns a pull request

- **WHEN** a writer assigns a reviewed pull request
- **THEN** no run of the workflow starts.

### Scenario: a reviewer is requested

- **WHEN** a writer requests a reviewer on a pull request, or removes that
  request
- **THEN** no run of the workflow starts.

### Scenario: an unrelated label is added

- **WHEN** a label other than `request-ai-review` is added while a requested
  review is queued
- **THEN** no review runs for the label, the queued review keeps its place, and
  `ai-review-present` in the label's run reports on the existing reviews.

### Scenario: a writer comments `@claude`

- **WHEN** a writer opens a pull request comment, review comment, or issue with
  `@claude`
- **THEN** no run of the workflow starts.

## Requirement: a pull request can block every AI review

While a pull request carries the `block-ai-reviews` label, no review SHALL run
for it, whatever event starts the run, an explicit `request-ai-review` included.
A `request-ai-review` added while the block is on SHALL stay on the pull
request, and removing `block-ai-reviews` SHALL start a run that reviews it. The
label SHALL NOT waive the `ai-review-present` gate.

Preflight SHALL read the pull request's labels when it runs, not from the event
payload. A label added after a run's preflight read them does not apply to that
run.

The gate SHALL NOT read the label, because a job skipped by its own `if:`
satisfies a required status check, and a label the gate honoured would let
anyone who can label a pull request self-waive the mandatory review. A blocked
pull request with no accepted review keeps a red gate, and only a user with
ruleset bypass can merge it.

### Scenario: a blocked pull request triggers the workflow

- **WHEN** a pull request carrying `block-ai-reviews` is opened or pushed to and
  no accepted review exists
- **THEN** no review responder runs, and `ai-review-present` runs and fails.

### Scenario: a blocked pull request already has an accepted review

- **WHEN** a pull request carrying `block-ai-reviews` has an accepted review and
  receives a push
- **THEN** no review responder runs, and `ai-review-present` passes on the
  existing review.

### Scenario: a writer requests a review on a blocked pull request

- **WHEN** a writer adds `request-ai-review` to a pull request carrying
  `block-ai-reviews`
- **THEN** no review runs, and `request-ai-review` stays on the pull request.

### Scenario: the block is lifted with a request waiting

- **WHEN** `block-ai-reviews` is removed from a pull request carrying
  `request-ai-review`
- **THEN** a run reviews the pull request, and its review job then removes
  `request-ai-review`.

## Requirement: the AI review verdict follows its findings

The review responder SHALL submit `APPROVE` when no validated finding remains or
every validated finding is non-blocking, and SHALL submit `REQUEST_CHANGES` when
any blocking finding remains, whether or not it is attached inline. It SHALL NOT
choose `COMMENT`, except as the retry when GitHub rejects a verdict because the
reviewer owns the pull request.

### Scenario: a re-review finds only non-blocking issues

- **WHEN** the AI reviewer earlier requested changes on a pull request and a
  re-review finds only non-blocking issues
- **THEN** the re-review is an `APPROVE` with inline comments, the reviewer's
  change request no longer blocks merge, and merge waits only for the inline
  threads to be resolved.

### Scenario: a review finds an anchored blocking issue

- **WHEN** a review finds a blocking issue and attaches it inline
- **THEN** the review is `REQUEST_CHANGES`, and the pull request stays blocked
  until a later review from the same reviewer approves it.

## Requirement: trusted-bot pull requests are approved without an AI review

The AI responder workflow SHALL approve a same-repository pull request whose
author is a `Bot` listed in `TRUSTED_BOT_ACTORS`, with a review body stating
that the AI review was skipped, only when every commit on the pull request is
authored by that bot, committed by that bot or `web-flow`, and carries a
verified signature, and only when that bot made the head branch's latest
creation and every push and force push since. When any commit or update fails
that check it SHALL NOT approve, and SHALL dismiss its own standing approval. It
SHALL NOT check out the pull request, SHALL NOT approve a pull request that
already carries its approval, and SHALL skip a run triggered by
`dependabot[bot]`, which cannot read the App secrets in the `plume-works-review`
environment.

### Scenario: Renovate opens a pull request

- **WHEN** `plume-works-renovate[bot]` opens a pull request on a branch of this
  repository
- **THEN** the workflow approves it once, no AI review runs, and
  `ai-review-present` passes on the trusted-bot waiver.

### Scenario: a bot outside the list opens a pull request

- **WHEN** a bot not listed in `TRUSTED_BOT_ACTORS` opens a pull request
- **THEN** no approval and no AI review is posted, and the pull request stays
  blocked unless merged by ruleset bypass.

### Scenario: a person pushes to a trusted-bot pull request

- **WHEN** an account other than the author bot pushes a commit that leaves the
  workflow unchanged to a trusted-bot pull request the workflow already approved
- **THEN** the workflow dismisses its approval, approves nothing, and the pull
  request needs a human approval to merge, even after it is closed and reopened.

### Scenario: a reused branch name starts clean

- **WHEN** a trusted bot recreates a branch whose earlier life included a
  person's push, and opens a new pull request from it
- **THEN** only the pushes since the branch's latest creation are checked, and
  the workflow approves the new pull request.
