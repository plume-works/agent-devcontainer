---
type: spec
description: How the required AI review gate accepts a review and when the responder is allowed to act on a pull request.
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/ai-review-status/action.yml
- resource: .github/actions/run-claude-responder/action.yml
- resource: data/architecture/assignee-review-trigger.md
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: data/architecture/ai-review-event-selection.md
- resource: data/plans/20261030-ai-review-verdicts-and-bot-approval.md
- resource: data/plans/20261107-drop-claude-task-responder.md
- resource: data/plans/20261030-responder-quill-app-identity.md
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
requested by removing the pull request's author as assignee and adding them
back, the way a human re-review is re-requested.

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
reopened, or assigned, and on a push to a pull request that has no accepted
review. An assignment SHALL run a review whether or not an accepted review
exists. The review job SHALL NOT run for a `pull_request` event on a draft pull
request.

The workflow SHALL be triggered only by pull request, pull request review, and
merge group events: a comment, an issue, or a mention of `@claude` SHALL start
no run, and the workflow SHALL accept no `workflow_dispatch`.

The `ai-review-present` gate SHALL run for pull request, pull request review,
and merge group events.

### Scenario: a draft is opened

- **WHEN** a pull request is opened as a draft
- **THEN** no review runs until the pull request is marked ready for review.

### Scenario: a writer re-requests a review by assignment

- **WHEN** a writer removes a reviewed pull request's author as assignee and
  adds them back
- **THEN** a `pull_request` run reviews the pull request, and its
  `ai-review-present` reports that review.

### Scenario: a writer comments `@claude`

- **WHEN** a writer opens a pull request comment, review comment, or issue with
  `@claude`
- **THEN** no run of the workflow starts.

## Requirement: a pull request can opt out of the AI review run

A pull request whose body carries `[ci:skip-ai-review]` alone on a line SHALL
skip the review responder, whatever event started the run, an assignment
included. The marker SHALL NOT waive the `ai-review-present` gate.

The marker SHALL be recognized only as a whole line, so that a body discussing
it — documentation, a migration note, a review comment quoted into the
description — reads as prose rather than as a directive. A substring match makes
every pull request that explains the feature disable review on itself.

The gate SHALL NOT read the marker, because a pull request body is
author-controlled and a job skipped by its own `if:` satisfies a required status
check. A marker that reached the gate would therefore let any author, fork
contributors included, self-waive the mandatory review. A marked pull request
with no accepted review keeps a red gate, and only a user with ruleset bypass
can merge it.

### Scenario: a marked pull request triggers the workflow

- **WHEN** a pull request body carries `[ci:skip-ai-review]` on its own line and
  no accepted review exists
- **THEN** no review responder runs, and `ai-review-present` runs and fails.

### Scenario: a marked pull request already has an accepted review

- **WHEN** a pull request body carries `[ci:skip-ai-review]` on its own line and
  an accepted review exists on it
- **THEN** no review responder runs, and `ai-review-present` passes on the
  existing review.

### Scenario: a body mentions the marker inline

- **WHEN** a pull request body names `[ci:skip-ai-review]` inside a sentence or
  a code span rather than alone on a line
- **THEN** the marker does not apply and the review responder runs normally.

### Scenario: a writer assigns a marked pull request

- **WHEN** a writer assigns a pull request whose body carries the marker on its
  own line
- **THEN** no review runs, and `ai-review-present` reports on the existing
  reviews.

## Requirement: a pull request review runs at a requested effort tier

The review responder SHALL support two effort tiers, `light` and `full`, which
select how many review passes run and which model size each pass uses. A tier
SHALL be requested by a `[ci:review-effort=light]` or `[ci:review-effort=full]`
marker alone on a line of the pull request body, and the marker SHALL be
recognized only as a whole line.

A requested tier SHALL be obeyed exactly. The review SHALL NOT escalate to a
higher tier, refuse, or fail on account of the diff it finds, whatever the
tier's fit for that diff.

When no tier is requested, the review SHALL size itself from the diff, and the
responder SHALL NOT override the model configured for the session.

An effort tier SHALL NOT change whether a review is required, SHALL NOT waive
the `ai-review-present` gate, and SHALL NOT suppress the pull request metadata
check or the durable-knowledge pass, which run at both tiers.

### Scenario: a body marker requests a tier

- **WHEN** a pull request body carries `[ci:review-effort=light]` on its own
  line
- **THEN** the review runs at the light tier.

### Scenario: a body mentions the effort marker inline

- **WHEN** a pull request body names `[ci:review-effort=light]` inside a
  sentence or a code span rather than alone on a line
- **THEN** the marker does not apply.

### Scenario: a light tier is requested for a large documentation change

- **WHEN** a pull request body requests the light tier and the diff is a large
  documentation rewrite
- **THEN** the review runs at the light tier, neither escalating nor failing.

### Scenario: no tier is requested

- **WHEN** no body marker requests a tier
- **THEN** the review sizes itself from the diff and runs with the session's
  configured model.

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
