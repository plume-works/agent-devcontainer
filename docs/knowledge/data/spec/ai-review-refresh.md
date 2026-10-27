---
type: spec
description: When the agentdev pr-* skills evaluate whether a reviewed pull request needs a fresh AI review, how they request one at most once per head commit, and how they judge a requested review's progress.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-25T16:39:29Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.sh
---

# AI review refresh

The [AI review gate](ai-review-gate.md) passes on any accepted AI review across
later pushes and leaves refreshing the review to the author. This spec states
how the agentdev catalog makes that call and carries it out.

## Requirement: every push to a reviewed pull request is evaluated

After any push to a pull request that has an accepted AI review, made through
`pr-open`'s update mode (and so `pr-sync`), `pr-merge`'s CI-fix step, or
`pr-feedback-resolution`, the agent SHALL apply `pr-eval-review-needed` and
report its decision, whether or not it requests a review. The evaluation SHALL
ask whether the diff since the newest reviewed commit goes beyond what the pull
request's review threads and review comments since that review asked for, read
from the pull request rather than from the session that made the change.

### Scenario: pr-sync pushes undirected behavior

- **WHEN** a reviewed pull request gains a behavior change no review thread
  asked for and `pr-sync` updates it
- **THEN** the run reports a re-review decision and requests a fresh review.

### Scenario: an update only applies requested feedback

- **WHEN** the diff since the newest reviewed commit only applies what the
  review threads and comments since that review asked for
- **THEN** the agent reports that no review is requested.

## Requirement: one AI review trigger per head commit

The catalog SHALL post an AI review trigger only through
`pr-request-ai-review`'s `request-review.sh`, and SHALL NOT post one for a head
commit that an accepted AI review already names or that already has a trigger,
whoever posted it. A comment is a trigger when its body opens with
`@claude review`, in any letter case. A trigger the script posts SHALL carry a
`review-head` marker naming its commit and SHALL count for that commit only; an
unmarked trigger SHALL count for the head only when it was created after the
earliest check suite on the head commit, so a head with no check suite has no
unmarked trigger counted for it. Accepted reviews are those the AI review gate
names, by author and state; a reaction names no commit and is not counted.

### Scenario: a second request for the same head

- **WHEN** a trigger marked for the head already exists
- **THEN** the script posts nothing and reports `ALREADY_REQUESTED` with that
  trigger's URL.

### Scenario: the head is already reviewed

- **WHEN** an accepted AI review names the head commit
- **THEN** the script posts nothing and reports `ALREADY_REVIEWED`.

### Scenario: a hand-typed trigger on the head

- **WHEN** an unmarked `@claude review` comment was created after the head's
  earliest check suite
- **THEN** the script posts nothing and reports `ALREADY_REQUESTED`.

### Scenario: a trigger that may belong to an earlier head

- **WHEN** the only unmarked trigger predates the head's earliest check suite,
  or the head has no check suite
- **THEN** the script posts a new marked trigger.

## Requirement: a requested review's status is read from the head commit's checks

The catalog SHALL judge a requested review as running when
`Claude PR Review Responder` or `ai-review-present` is pending on the pull
request's head commit, and as finished when the latest `ai-review-present` run
on the head completes, reading both from `gh pr checks`. It SHALL NOT look up
the review workflow by name or follow a run by id to decide either. When a
trigger produces no check on the head, the cause SHALL be read from the
`issue_comment` run of `ai-responder.yml` on the default branch and reported for
a person rather than retried.

### Scenario: confirming a posted request

- **WHEN** a trigger is posted and `Claude PR Review Responder` is pending on
  the head commit
- **THEN** the agent reports the review as started and waits on the head's
  checks instead of posting again.

### Scenario: a trigger that dispatched nothing

- **WHEN** no review check appears on the head and the `issue_comment` run's
  preflight failed or its bridge skipped or failed
- **THEN** the agent reports that a fork, a head branch without
  `ai-responder.yml`, or a rejected requester needs a person, and posts no
  further trigger.
