# AI review refresh Specification

## Purpose

When the agentdev pr-* skills evaluate whether a reviewed pull request needs a fresh AI review, how they request one at most once per head commit and its title and description, and how they judge a requested review's progress.

The [AI review gate](../ai-review-gate/spec.md) passes on any accepted AI review across
later pushes and leaves refreshing the review to the author. This spec states
how the agentdev catalog makes that call and carries it out.

## Requirements

### Requirement: every push to a reviewed pull request is evaluated

After any push to a pull request that has an accepted AI review, made through
`pr-open`'s update mode (and so `pr-sync`), `pr-merge`'s CI-fix step, or
`pr-feedback-resolution`, the agent SHALL apply `pr-eval-review-needed` and
report its decision, whether or not it requests a review. When the AI reviewer's
newest verdict — its latest review in state `APPROVED` or `CHANGES_REQUESTED` —
is `CHANGES_REQUESTED`, the evaluation SHALL request a review whatever the diff
holds. Otherwise the evaluation SHALL ask whether the diff since the newest
reviewed commit goes beyond what the pull request's review threads and review
comments since that review asked for, read from the pull request rather than
from the session that made the change.

#### Scenario: pr-sync pushes undirected behavior

- **WHEN** a reviewed pull request gains a behavior change no review thread
  asked for and `pr-sync` updates it
- **THEN** the run reports a re-review decision and requests a fresh review.

#### Scenario: an update only applies requested feedback

- **WHEN** the AI reviewer's newest verdict is `APPROVED` and the diff since the
  newest reviewed commit only applies what the review threads and comments since
  that review asked for
- **THEN** the agent reports that no review is requested.

#### Scenario: an update answers a change request

- **WHEN** the AI reviewer's newest verdict is `CHANGES_REQUESTED` and the diff
  since that review only applies what its threads asked for
- **THEN** the agent requests a fresh review and reports the change request as
  the reason.

### Requirement: one AI review trigger per head commit

The catalog SHALL request an AI review only through `pr-request-ai-review`'s
`request-review.py`, and SHALL request it by adding the `request-ai-review`
label to the pull request. The catalog SHALL NOT change the pull request's
assignees to request a review, and SHALL NOT post an `@claude review` comment.

While the pull request carries `block-ai-reviews`, the script SHALL first report
`ALREADY_REVIEWED` or `ALREADY_REQUESTED` where the rules below find the input
reviewed or a responder check requesting it; otherwise it SHALL add
`request-ai-review` unless it is already present, and SHALL report `BLOCKED`,
because no review can run until the block is lifted.

A review's input is the head commit together with the pull request's title and
description, which a review run reads when it starts. While the pull request
already carries the label and is not blocked, the script SHALL NOT add it when a
run of `ai-responder.yml` on the head branch is unfinished, because a run in the
pull request's concurrency group takes the label; with no unfinished run the
label is stale, and the script SHALL remove it and add it again. The script
SHALL NOT add the label for a head commit that an accepted AI review already
names, submitted after the latest title or description edit by a run that
started after it, or that carries a `Claude PR Review Responder` check run that
is queued, in progress, or started after that edit and completed with a
conclusion other than `skipped` or `cancelled`, whoever started it. A review
submitted while a responder run that started before the edit was running SHALL
NOT count. When the pull request was never edited, every such review and check
counts. Accepted reviews are those the AI review gate names, by author and
state; a reaction names no commit and is not counted.

A rationale, when given, SHALL be posted as a pull request comment that opens
with `AI review requested for <sha>:` and carries no `@claude` mention.

#### Scenario: a second request for the same head

- **WHEN** a `Claude PR Review Responder` check on the head is queued, in
  progress, or started after the latest title or description edit and completed
  with a failure
- **THEN** the script adds no label and reports `ALREADY_REQUESTED` with that
  check's URL.

#### Scenario: the label is waiting for a run

- **WHEN** the pull request carries `request-ai-review`, does not carry
  `block-ai-reviews`, and a run of `ai-responder.yml` on the head branch is
  unfinished
- **THEN** the script adds no label and reports `ALREADY_REQUESTED`.

#### Scenario: the pull request is blocked

- **WHEN** the pull request carries `block-ai-reviews`, and no accepted review
  or responder check covers its input
- **THEN** the script adds `request-ai-review` unless it is already present, and
  reports `BLOCKED`.

#### Scenario: a blocked pull request that is already reviewed

- **WHEN** the pull request carries `block-ai-reviews`, and an accepted AI
  review already names its head after the latest title or description edit
- **THEN** the script adds no label and reports `ALREADY_REVIEWED`, so lifting
  the block does not review the same input again.

#### Scenario: the label is stale

- **WHEN** the pull request carries `request-ai-review` and no run of
  `ai-responder.yml` on the head branch is unfinished
- **THEN** the script removes the label, adds it again, and reports `SUCCESS`.

#### Scenario: the head is already reviewed

- **WHEN** an accepted AI review submitted after the latest title or description
  edit names the head commit
- **THEN** the script adds no label and reports `ALREADY_REVIEWED`.

#### Scenario: the description changed after the head's review

- **WHEN** every completed responder check on the head started before the latest
  title or description edit, every accepted AI review naming the head was
  submitted before that edit or by one of those runs, and no responder check on
  the head is queued or in progress
- **THEN** the script adds `request-ai-review` and reports `SUCCESS`.

#### Scenario: the description changed while a review was running

- **WHEN** the title or description is edited after a responder run on the head
  started, and that run finishes and submits its review after the edit
- **THEN** neither the run's check nor its review counts, and once no responder
  check is queued or in progress the script adds `request-ai-review` and reports
  `SUCCESS`.

#### Scenario: a push to a reviewed pull request

- **WHEN** the only `Claude PR Review Responder` check on the head was skipped
- **THEN** the script adds `request-ai-review` and reports `SUCCESS`.

#### Scenario: a request with a rationale

- **WHEN** the script adds the label with `--rationale`
- **THEN** it posts one comment opening `AI review requested for <sha>:` with
  the rationale, and no workflow run starts for it.

### Requirement: a requested review's status is read from the head commit's checks

The catalog SHALL judge a requested review as running when
`Claude PR Review Responder` or `ai-review-present` is pending on the pull
request's head commit, and as finished when the latest `ai-review-present` run
on the head completes, reading both from `gh pr checks`. It SHALL NOT look up
the review workflow by name or follow a run by id to decide either. When a
request produces no review check on the head, the cause SHALL be read from the
`pull_request` run of `ai-responder.yml` on the head branch, or from its
absence, and reported for a person rather than retried.

#### Scenario: confirming a request

- **WHEN** the script adds the label and `Claude PR Review Responder` is pending
  on the head commit
- **THEN** the agent reports the review as started and waits on the head's
  checks instead of requesting again.

#### Scenario: a request that reviewed nothing

- **WHEN** no review check runs on the head because adding the label started no
  `pull_request` run, or that run skipped or failed its preflight
- **THEN** the agent reports, respectively, a token whose events start no
  workflow, a bot-authored or fork pull request, or a requester without write
  access as needing a person, and requests no further review.
