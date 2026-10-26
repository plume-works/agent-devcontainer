---
type: plan
created: 2026-10-26
release:
- features/ai-responder-workflows
- bugs/dispatched-review-gate-not-counted
description: Make a pull_request assignment the only way to request an AI re-review, reject `@claude review` comments with a pointer to the assignee toggle, stop dispatched runs from reviewing, take the effort tier from the body marker alone, and drop Codex from the AI review gate.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-26T05:00:00Z
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/ai-review-status/action.yml
- resource: docs/knowledge/data/spec/ai-review-gate.md
- resource: docs/knowledge/data/architecture/assignee-review-trigger.md
---

# Assignee-triggered AI re-reviews replace the comment trigger

## Context

Fixes [Bug: a comment-requested review's gate does not count toward
merge](../bugs/dispatched-review-gate-not-counted.md), and changes [AI responder
workflows](../features/ai-responder-workflows.md).

An `@claude review` comment runs its review as a `workflow_dispatch` on the head
branch. That run's `ai-review-present` is not counted by the pull request rollup
or the `main` ruleset, so it neither holds a merge nor clears a red gate. A
`pull_request`/`assigned` run is counted. It reviews whether or not an accepted
review exists, and its gate is the one the ruleset reads. [Assignee-triggered AI
re-reviews](../architecture/assignee-review-trigger.md) records those
behaviours, the maintainer's decisions, and the alternatives they rule out.

The maintainer decided on 2026-10-26:

- an assignment is the re-review trigger;
- `@claude review` comments are rejected with the approved message, as a failed
  bridge run plus a reply on the pull request;
- the `[ci:skip-ai-review]` marker is always respected, whatever triggered the
  run;
- the per-request effort tier goes with the comment, and the body marker stays;
- Codex reviews are removed, since no consumer relies on them;
- a queued review dropped by a later pull request event is accepted, because
  only the latest review matters;
- bot-authored pull requests outside `TRUSTED_BOT_ACTORS` get no AI review and
  merge only by ruleset bypass;
- this plan ships before [PR skills drive the AI review lifecycle on the single
  review workflow](20261023-pr-skills-ai-review-lifecycle.md), which moves its
  trigger script and skills onto the assignee toggle.

## Approach

Reviews come only from `pull_request` events: `opened`, `ready_for_review`,
`reopened`, and `assigned` always review, and a push reviews a pull request that
has no accepted review. `workflow_dispatch` keeps carrying free-form tasks until
[Drop the `@claude <custom prompt>` free-form task
trigger](../backlog/drop-claude-free-form-task-trigger.md) removes them. A
dispatch therefore requires a task, and an empty one fails preflight. The bridge
still dispatches `@claude <prompt>` task mentions. A mention that opens
`@claude review` (case folded) instead fails the bridge job and posts the
approved message as a pull request comment. That needs `pull-requests: write` on
the bridge job alone. With no dispatch reviewing, `ai-review-present` runs for
`pull_request`, `pull_request_review`, and `merge_group` events only. The effort
tier comes from `[ci:review-effort=…]` alone, so the `review_effort` input and
its comment parse go. `ai-review-status` accepts only `claude[bot]` and
`github-actions[bot]` reviews.

Assumption, not decided by the maintainer: an empty-task `workflow_dispatch`
fails preflight rather than reviewing. A dispatched review's gate is not
counted, so keeping that path would keep the bug for anyone who dispatches by
hand.

Rejected:

- keeping dispatched reviews with the comment trigger rejected, which leaves an
  uncounted review path;
- letting an assignment outrank the skip marker or review a bot-authored pull
  request, both declined by the maintainer;
- replying to a review-comment mention in its thread instead of on the
  conversation, which gives one rejection path two API shapes for a message that
  points at the same toggle.

## Implementation Steps

### Task 1: The gate accepts Claude reviews only

**Files:** Modify: `.github/actions/ai-review-status/action.yml`

- [x] `codexLogins`, the Codex review lookup, and the `+1` reaction lookup are
  removed. The failure message names only `claude[bot]` and
  `github-actions[bot]`. `actionlint` and `zizmor` pass.
  - **Evidence:** commit "Accept only Claude reviews in the AI review gate" —
    `ai-review-status/action.yml` -37/+6; `pre-commit run actionlint` and
    `pre-commit run zizmor --all-files` passed.

### Task 2: Only pull request events review

**Files:** Modify: `.github/workflows/ai-responder.yml`

- [x] In preflight's `wantsReview`, a `workflow_dispatch` never reviews.
  Preflight fails a dispatch whose `task` is empty, naming the assignee toggle.
  The comment claiming an explicit request outranks the marker is removed. The
  marker check stays ahead of the action rules.
  - **Evidence:** commit "Stop dispatched runs from reviewing and read the tier
    from the body marker" — the empty-task throw opens
    `Determine agent prompts`, and `wantsReview` starts at the skip-marker
    check; `pre-commit run actionlint --all-files` and
    `pre-commit run zizmor --all-files` passed.
- [x] `ai-review-present`'s `if:` drops the empty-task `workflow_dispatch`
  clause.
  - **Evidence:** commit "Stop dispatched runs from reviewing and read the tier
    from the body marker" — the `if:` lists `pull_request`,
    `pull_request_review`, and `merge_group` only; `actionlint` passed.
- [x] The `review_effort` dispatch input, `DISPATCH_REVIEW_EFFORT`, and its
  precedence over the body marker are removed. `reviewEffort` comes from
  `[ci:review-effort=…]` alone.
  - **Evidence:** commit "Stop dispatched runs from reviewing and read the tier
    from the body marker" — the Verification grep for `inputs.review_effort`,
    `DISPATCH_REVIEW_EFFORT`, and the input key returns nothing.

### Task 3: The bridge rejects `@claude review`

**Files:** Modify: `.github/workflows/ai-responder.yml`

- [x] The bridge job handles a mention whose body opens `@claude review` (case
  folded) without dispatching. It posts the message below as a comment on the
  pull request, then fails the job with the same message. Its `reviewEffort`
  parse and empty-task dispatch are removed. Other `@claude` mentions dispatch
  as tasks, unchanged.

  ```
  `@claude review` is no longer supported. To request an AI review, remove the pull request's author as assignee and add them back.
  ```

  - **Evidence:** commit "Reject `@claude review` in the bridge with a pointer
    to the assignee toggle" — the rejection branch runs before the head-branch
    lookup, posts the message with `issues.createComment`, and calls
    `core.setFailed` with it; other mentions dispatch with `task: body`.
    `pre-commit run actionlint --all-files` passed. Live behaviour is Task 6.

- [x] The bridge job gains `pull-requests: write` and nothing else. `zizmor`
  passes.

  - **Evidence:** commit "Reject `@claude review` in the bridge with a pointer
    to the assignee toggle" — bridge permissions are `actions: write`,
    `contents: read`, `pull-requests: write`;
    `pre-commit run zizmor --all-files` passed.

### Task 4: Documentation names the assignee trigger

**Files:** Modify: `README.md`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`,
`docs/knowledge/data/features/ai-responder-workflows.md`,
`.agents/plugins/agentdev/skills/pr-review/SKILL.md`

- [x] The README "Pull-request automation" section names removing and re-adding
  the author as assignee as the way to request another review.
  - **Evidence:** commit "Document the assignee toggle as the AI re-review
    trigger" — `README.md` "Pull-request automation" replaces the
    `@claude review` sentence with the assignee toggle.
- [x] The consumption guide's `@claude review` references are rewritten:
  - the untrusted-bot note says such pull requests need ruleset bypass;
  - the run-link note is limited to comment-triggered task requests;
  - the re-review trigger behaviour names the assignee toggle;
  - the default-branch caveat covers task mentions and the rejection.
  - **Evidence:** commit "Document the assignee toggle as the AI re-review
    trigger" — `consumption-guide.md` -8/+8 covering all four points; the
    Verification `@claude review` grep shows only the default-branch rejection
    note.
- [x] The feature doc drops Codex acceptance and the comment re-review, states
  that the marker outranks an assignment, and takes the effort tier from the
  body marker alone.
  - **Evidence:** commit "Document the assignee toggle as the AI re-review
    trigger" — `ai-responder-workflows.md` gate, skip-marker, and effort
    paragraphs rewritten; `iwe normalize` and `iwe schema validate` passed.
- [x] `pr-review/SKILL.md` names the body marker as the only source of the
  effort tier, and its trigger example no longer offers `@claude review` or
  `@codex review`.
  `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes.
  - **Evidence:** commit "Document the assignee toggle as the AI re-review
    trigger" — `pr-review/SKILL.md` lines 14 and 87; the validator reported
    64/64 skills valid, 0 errors, 0 warnings.

### Task 5: Assignment reviews on a live pull request

**Files:** none (CI evidence)

- [ ] On a throwaway same-repository pull request whose head already passed
  `ai-review-present`, removing and re-adding the author runs a
  `pull_request`/`assigned` review, and its `ai-review-present` appears in
  `gh pr checks`.
- [ ] On a throwaway pull request whose body carries `[ci:skip-ai-review]` and
  that has no accepted review, assigning the author runs no review, and
  `ai-review-present` fails.

### Task 6: The bridge rejects `@claude review` once on `main`

**Files:** none (CI evidence). It stands alone, because GitHub resolves
`issue_comment` against the default branch's workflow file.

- [ ] After merge, an `@claude review` comment on a throwaway pull request gets
  the approved message as a reply, the bridge job fails with it, and no review
  run starts.
- [ ] After merge, an `@claude <task>` comment still dispatches a task run.

## Spec changes

[AI review gate](../spec/ai-review-gate.md):

``` markdown
## MODIFIED Requirements

## Requirement: PRs are blocked until an AI review exists

A pull request SHALL NOT be mergeable until Claude has reviewed it. The
`ai-review-present` check SHALL accept a review from `claude[bot]` or
`github-actions[bot]` in state `approved`, `changes_requested`, or
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

## Requirement: a review runs on first push and on explicit request

The review job SHALL run when a pull request is opened, marked ready for review,
reopened, or assigned, and on a push to a pull request that has no accepted
review. An assignment SHALL run a review whether or not an accepted review
exists. The review job SHALL NOT run for a `pull_request` event on a draft pull
request, and SHALL NOT run for a `workflow_dispatch`. A `workflow_dispatch`
SHALL carry a free-form task, and one whose task is empty SHALL fail preflight.

The `ai-review-present` gate SHALL run for pull request, pull request review,
and merge group events. It SHALL NOT run for `workflow_dispatch` events.

### Scenario: a draft is opened

- **WHEN** a pull request is opened as a draft
- **THEN** no review runs until the pull request is marked ready for review.

### Scenario: a writer re-requests a review by assignment

- **WHEN** a writer removes a reviewed pull request's author as assignee and
  adds them back
- **THEN** a `pull_request` run reviews the pull request, and its
  `ai-review-present` reports that review.

### Scenario: a dispatch carries no task

- **WHEN** `ai-responder.yml` is dispatched with an empty `task`
- **THEN** preflight fails and no review runs.

## Requirement: a pull request can opt out of the AI review run

A pull request whose body carries `[ci:skip-ai-review]` alone on a line SHALL
skip the review responder, whatever event started the run, an assignment
included. The marker SHALL NOT waive the `ai-review-present` gate, and SHALL NOT
disable free-form responder tasks.

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

### Scenario: a marked pull request requests a free-form task

- **WHEN** a writer requests a free-form `@claude` task on a pull request whose
  body carries `[ci:skip-ai-review]`
- **THEN** the task responder runs.

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

## Requirement: comment mentions run the pull request branch's workflow

A `@claude` mention opening a comment, review, or review comment on a pull
request SHALL be answered by a `workflow_dispatch` of this workflow on the pull
request's head branch, carrying the mention as a free-form task, so the run
executes the branch's own workflow file. The dispatched responder run SHALL
append its run link to the requesting comment, review, or review comment before
Claude starts.

A mention that opens with `@claude review`, matched case-insensitively, SHALL
NOT be dispatched. The bridge SHALL post the following message as a comment on
the pull request and fail with the same message:

`@claude review` is no longer supported. To request an AI review, remove the pull request's author as assignee and add them back.

### Scenario: a writer requests a free-form task on a pull request

- **WHEN** a writer opens a pull request comment with `@claude` followed by a
  task
- **THEN** a run of this workflow starts on the head branch, runs the task, and
  appends its run link to the comment.

### Scenario: a writer comments `@claude review`

- **WHEN** a writer opens a pull request comment with `@claude review`
- **THEN** no run is dispatched, the message above is posted on the pull
  request, and the bridge job fails.

A dispatch SHALL carry only the inputs the request actually supplies. A head
branch's workflow file declares its own inputs, and a dispatch naming one the
branch does not declare is rejected on the key alone, whatever its value.

### Scenario: the head branch has no workflow file

- **WHEN** the pull request's head branch does not carry `ai-responder.yml`
- **THEN** the bridge fails naming the branch, and no task runs.
```

## Verification

- `pre-commit run actionlint --all-files` and
  `pre-commit run zizmor --all-files` pass.
- `grep -rn 'codex' .github/actions/ai-review-status/action.yml` returns
  nothing.
- `grep -n "inputs.review_effort\|DISPATCH_REVIEW_EFFORT\|^      review_effort:$" .github/workflows/ai-responder.yml`
  returns nothing.
- `grep -rn '@claude review' README.md .agents/plugins/agentdev/skills/pr-review .agents/plugins/agentdev/skills/template-consume docs/knowledge/data/features/ai-responder-workflows.md`
  shows only rejection notes.
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes.
- Tasks 5 and 6 are closed with their run and pull request evidence.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- The trigger script and the `pr-request-ai-review`, `pr-merge`, and
  `pr-eval-review-needed` skills. [PR skills drive the AI review lifecycle on
  the single review workflow](20261023-pr-skills-ai-review-lifecycle.md) moves
  them onto the assignee toggle, which restores an author who was not assigned
  before the trigger.
- Free-form `@claude <prompt>` tasks, kept until [Drop the
  `@claude <custom prompt>` free-form task
  trigger](../backlog/drop-claude-free-form-task-trigger.md).
- Whether auto-merge waits for an assigned review, which belongs to [Verify that
  auto-merge waits for an assignee-triggered
  review](../backlog/verify-assignee-review-automerge.md).
- A review dropped from the `pr-<n>` concurrency queue by a later pull request
  event, accepted by decision.
- AI review of bot-authored pull requests outside `TRUSTED_BOT_ACTORS`, which
  stay unreviewed by decision.
- `docs/knowledge/data/architecture/pr-review-effort-tiers.md`, a decision
  record that [Assignee-triggered AI
  re-reviews](../architecture/assignee-review-trigger.md) supersedes for the
  comment tier.

## Key references

Verified anchor points (line numbers as of 2026-10-26):

- `.github/workflows/ai-responder.yml:95` — preflight `if:`, excluding
  bot-authored and fork `pull_request` events
- `.github/workflows/ai-responder.yml:253` — preflight failure for an empty-task
  dispatch
- `.github/workflows/ai-responder.yml:261` — skip-marker check
- `.github/workflows/ai-responder.yml:267` — actions that always review,
  including `assigned`
- `.github/workflows/ai-responder.yml:275` — `reviewEffort` from the body marker
- `.github/workflows/ai-responder.yml:348` — `bridge` job
- `.github/workflows/ai-responder.yml:360` — bridge `pull-requests: write`
- `.github/workflows/ai-responder.yml:376` — bridge rejection of
  `@claude review`
- `.github/workflows/ai-responder.yml:400` — bridge task dispatch
- `.github/workflows/ai-responder.yml:507` — `ai-review-present` `if:`
- `.github/actions/ai-review-status/action.yml:68` — `claudeLogins`, the only
  accepted reviewers
- `.github/actions/ai-review-status/action.yml:97` — failure message
- `README.md:318` — assignee-toggle re-review instruction
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:420`
  — untrusted-bot note
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:448`
  — re-review by assignee toggle
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:14` — trigger example
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:87` — effort-tier source
- `docs/knowledge/data/features/ai-responder-workflows.md:70` — gate acceptance
  and re-review paragraph
