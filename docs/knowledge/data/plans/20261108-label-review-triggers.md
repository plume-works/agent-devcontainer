---
type: plan
created: 2026-11-08
release:
- features/ai-responder-workflows
description: Request an AI re-review with a one-shot request-ai-review label and suppress automatic reviews with a skip-ai-review label, replacing the assignee trigger, the [ci:skip-ai-review] body marker, and the [ci:review-effort=…] tiers.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-08T01:30:00Z
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/run-claude-responder/action.yml
- resource: .agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: docs/knowledge/data/architecture/assignee-review-trigger.md
- resource: docs/knowledge/data/architecture/pr-review-effort-tiers.md
- resource: docs/knowledge/data/spec/ai-review-gate.md
- resource: docs/knowledge/data/spec/ai-review-refresh.md
rank: 950
---

# AI reviews are requested and skipped with labels

## Context

Changes [AI responder workflows](../features/ai-responder-workflows.md).

A re-review is requested today by removing the pull request's author as assignee
and adding them back ([Assignee-triggered AI
re-reviews](../architecture/assignee-review-trigger.md)). The maintainer's goal
is an easy, trusted, explicit way to request a re-review.

A label applied to a pull request fires `pull_request`/`labeled`, a
`pull_request` event like `assigned`, so its run is counted by the `main`
ruleset and the pull request's status rollup, and its checks land on the head
commit.

The maintainer decided on 2026-11-08:

- a `request-ai-review` label is the one way to request a review; the label is
  on the pull request only from the moment someone adds it until a run accepts
  or rejects it, and preflight removes it with `GITHUB_TOKEN` when the run
  starts;
- `assigned` no longer requests a review, so an assignee means ownership only;
- `review_requested` and `review_request_removed` are no longer triggers: no
  review comes from them, and each started a run;
- a `skip-ai-review` label replaces the `[ci:skip-ai-review]` body marker; it
  stays until someone removes it and suppresses only the automatic reviews on
  open, ready-for-review, reopen, and push; an explicit `request-ai-review`
  always runs a review;
- the `[ci:review-effort=light|full]` marker and requested effort tiers are
  removed; every review sizes itself;
- this plan lands before [Resume interrupted Claude PR review
  sessions](20260909-resumable-claude-review-sessions.md), which is revised
  afterwards to build on the `labeled` trigger and concurrency split this plan
  adds.

A `skip-ai-review` label saves the review runs that would fail while Claude is
unavailable. It does not let a pull request merge without ruleset bypass,
because `ai-review-present` still requires an accepted review.

## Approach

```
 add request-ai-review ──► pull_request/labeled ──► concurrency pr-<n>
                                                     │
 add any other label ────► pull_request/labeled ──► concurrency label-<run id>
                                                     │
 preflight ── removes request-ai-review (GITHUB_TOKEN, issues: write)
          ├── reads current labels from the API
          ├── wantsReview: request-ai-review            → yes (skip label ignored)
          │                opened/ready/reopened/push*   → yes unless skip-ai-review
          │                anything else                 → no
          ▼
 claude-respond (if wantsReview) ──► ai-review-present (every run, never skipped)

 * push only while no accepted review exists
```

`ai-responder.yml` adds `labeled` and drops `assigned`, `review_requested`, and
`review_request_removed` from its `pull_request` types. The workflow-level
concurrency group sends a `labeled` event for any label other than
`request-ai-review` to a group of its own, keyed by run id, so adding an
unrelated label never replaces a review queued in `pr-<n>`. `ai-review-present`
keeps running in those runs and evaluates the existing reviews: a job skipped by
its own `if:` satisfies a required check, so skipping the gate for an unrelated
label would let anyone with triage access turn it green.

Preflight removes `request-ai-review` in its first step, before authorization,
so a request is cleared whether the run accepts it or rejects it. It reads the
pull request's labels from the API rather than the event payload, so a
`skip-ai-review` label added right after the pull request was created is seen by
the `opened` run whenever it lands before preflight reads it.

The effort marker, the `review_effort` output, the light-tier model override,
and `run-claude-responder`'s `model` input are removed. `pr-review` keeps its
internal effort matrix for self-sizing and loses only the requested-tier route.

`request-review.py` requests a review by adding `request-ai-review`, and treats
the label already being on the pull request as a pending request. Every catalog
skill, the specs, the feature doc, the README, and the consumption guide follow.
A new architecture note supersedes `assignee-review-trigger` and
`pr-review-effort-tiers`, which are left unedited.

Known limits:

- A run started by an unrelated label evaluates the gate on the existing
  reviews, so while a requested review is still running, that run's gate can
  report a result the pending review later replaces.
- Preflight does not run on fork or bot-authored pull requests, so a
  `request-ai-review` added there stays until someone removes it; no review can
  run on them either way.
- An `opened` run whose preflight reads the labels before a creation-time
  `skip-ai-review` lands still reviews.

Rejected alternatives:

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

Assumptions:

- Adopting repositories create both labels; the consumption guide says so.
- The pending-request check in `request-review.py` reads the labels on the pull
  request, so a label added by another person also counts as a pending request.

## Implementation Steps

### Task 1: Labels start and route runs

**Files:** Modify: `.github/workflows/ai-responder.yml`

- [x] The `pull_request` types are `opened`, `reopened`, `ready_for_review`,
  `synchronize`, and `labeled`.
  - **Evidence:** commit 4b349b9b; `on.pull_request.types` lists `opened`,
    `reopened`, `ready_for_review`, `synchronize`, `labeled`; actionlint passes.
- [x] The concurrency group of a `labeled` event for a label other than
  `request-ai-review` is unique to its run, and every other `pull_request` event
  keeps `pr-<n>`.
  - **Evidence:** commit 4b349b9b; the group expression maps a `labeled` event
    whose `github.event.label.name` is not `request-ai-review` to
    `label-<run id>` before the `pr-<n>` branch; actionlint and zizmor pass.

### Task 2: Preflight honours the two labels

**Files:** Modify: `.github/workflows/ai-responder.yml`

- [x] Preflight's first step removes `request-ai-review` from the pull request
  when the event added it, with `GITHUB_TOKEN` holding `issues: write`.
  - **Evidence:** commit ebfe8ab4; the first preflight step, "Clear the review
    request label", runs when the event added `request-ai-review` and calls
    `github.rest.issues.removeLabel`, tolerating a 404; preflight's
    `GITHUB_TOKEN` holds `issues: write`; actionlint and zizmor pass.
- [x] Preflight reads the pull request's current labels from the API.
  - **Evidence:** commit ebfe8ab4; "Determine checkout ref" pages
    `github.rest.issues.listLabelsOnIssue` for the pull request; actionlint
    passes.
- [x] `wantsReview` is true for a `labeled` event adding `request-ai-review`,
  whatever other labels the pull request carries, and false for every other
  `labeled` event.
  - **Evidence:** commit ebfe8ab4; `wantsReview` returns
    `payload.label?.name === 'request-ai-review'` for every `labeled` event
    before the skip check, after the draft check; every inline script parses
    under `bun build --no-bundle`.
- [x] `skip-ai-review` makes `wantsReview` false for `opened`,
  `ready_for_review`, `reopened`, and `synchronize`; the `[ci:skip-ai-review]`
  body regex is removed.
  - **Evidence:** commit ebfe8ab4; "Determine checkout ref" sets `skipAiReview`
    from the `skip-ai-review` label and the `[ci:skip-ai-review]` regex is gone;
    `wantsReview` returns false for `opened`, `ready_for_review`, `reopened`,
    and `synchronize` when it is set; every inline script parses under
    `bun build --no-bundle`.
- [x] `ai-review-present` runs for every `labeled` event.
  - **Evidence:** commit ebfe8ab4 with b0b10399; the gate's `if:` is `always()`
    for every `pull_request` event and `labeled` is a `pull_request` type, so no
    label skips it; actionlint passes.

### Task 3: Requested effort tiers are removed

**Files:** Modify: `.github/workflows/ai-responder.yml`,
`.github/actions/run-claude-responder/action.yml`,
`.agents/plugins/agentdev/skills/pr-review/SKILL.md`

- [x] The workflow has no `[ci:review-effort=…]` regex, `review_effort` output,
  `REQUESTED REVIEW EFFORT` prompt line, or light-tier `model` override.
  - **Evidence:** commit e6171e7e; the effort regex, the `review_effort` output,
    the `REQUESTED REVIEW EFFORT` prompt line, and the `claude-sonnet-5`
    override are gone; every inline script parses under `bun build --no-bundle`,
    and actionlint passes.
- [x] `run-claude-responder` has no `model` input.
  - **Evidence:** commit e6171e7e; the `model` input is gone and "Compose Claude
    arguments" emits only `--allowedTools`; zizmor passes.
- [x] `pr-review`'s `## Effort Tiers` drops the requested-tier route and says
  the review always sizes itself, keeping the effort matrix it sizes with.
  - **Evidence:** commit e6171e7e; `## Effort Tiers` says nothing requests a
    tier, drops "A requested tier is absolute", keeps the size and slot tables,
    and the validation bullet names a self-sized review; `validate_agent_files`
    reports 0 errors.

### Task 4: The catalog requests a review with the label

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py`,
`.agents/plugins/agentdev/tests/test_request_review.py`,
`.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md`

- [x] `request-review.py` requests a review by adding `request-ai-review` and no
  longer touches assignees.
  - **Evidence:** commit 996fd4b7; the script POSTs `labels[]=request-ai-review`
    to `issues/<n>/labels` and has no assignee call;
    `test_request_adds_the_label` and `test_assignees_are_never_touched` pass.
- [x] It reports `ALREADY_REQUESTED` when `request-ai-review` is already on the
  pull request.
  - **Evidence:** commit 996fd4b7; `run()` returns `ALREADY_REQUESTED` when the
    pull request's `labels` include `request-ai-review`, before any write;
    `test_label_already_present_is_already_requested` passes.
- [x] Tests cover the label being added, the label already present, and that no
  assignee call is made.
  - **Evidence:** commit 996fd4b7;
    `uv run pytest .agents/plugins/agentdev/tests/test_request_review.py` passes
    38 tests, including `test_request_adds_the_label`,
    `test_label_already_present_is_already_requested`, and
    `test_assignees_are_never_touched`.
- [x] `SKILL.md` describes the label request and its confirmation.
  - **Evidence:** commit 996fd4b7; "Post the request" and "Confirm it started"
    describe adding `request-ai-review`, the label as a pending request, and the
    causes when no review starts; `validate_agent_files` reports 0 errors,
    prettier passes.

### Task 5: Merge and evaluation skills follow the label

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-merge/SKILL.md`

- [x] `## AI Review Recovery` describes requesting with `request-ai-review` and
  treats an added label, a started run, or a pending review as not yet complete.
  - **Evidence:** commit f8602763; `## AI Review Recovery` says a review is
    requested by adding `request-ai-review`, reads `ALREADY_REQUESTED` as a
    waiting label or a covering check, and does not treat an added label, a
    started run, or a pending review as completion; `validate_agent_files`
    passes in the pre-commit hook.

### Task 6: Consumer docs describe the labels

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`,
`README.md`, `docs/knowledge/data/features/ai-responder-workflows.md`

- [x] The consumption guide adds creating the `request-ai-review` and
  `skip-ai-review` labels to the required prerequisites and describes requesting
  and skipping a review with them.
  - **Evidence:** commit ba52ceed; "AI responder and the review gate" lists
    creating `request-ai-review` and `skip-ai-review` as the third required
    prerequisite, describes refreshing a review with the label and the trigger
    behaviour, and the Workflow B summary names the labels;
    `validate_agent_files` reports 0 errors.
- [x] `README.md` says to add `request-ai-review` to request another review.
  - **Evidence:** commit ba52ceed; "Pull-request automation" says to add
    `request-ai-review` to request another review and lists both labels among
    the adopter prerequisites; prettier passes.
- [x] The feature's `## Behaviour` describes both labels, drops the assignee
  trigger, the body markers, and requested tiers, and links the new note.
  - **Evidence:** commit ba52ceed; `## Behaviour` describes `request-ai-review`
    and `skip-ai-review`, says assignment, reviewer requests, and
    `@claude review` start nothing, replaces the effort-tier paragraph with
    "Every review sizes itself.", and links
    `architecture/label-review-triggers`; `iwe schema validate` passes.
- [x] `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
  - **Evidence:** commit ba52ceed;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    reports 0 errors and 0 warnings.

### Task 7: Architecture note records the label triggers

**Files:** Create: `docs/knowledge/data/architecture/label-review-triggers.md`;
Modify: `docs/knowledge/data/architecture.md`

- [ ] The note records the decisions under `## Context`, the routing under
  `## Approach`, its known limits, and every rejected alternative, and states
  that it supersedes [Assignee-triggered AI
  re-reviews](../architecture/assignee-review-trigger.md) and [PR review effort
  tiers](../architecture/pr-review-effort-tiers.md), which are left unedited.
- [ ] The note is linked from `data/architecture.md`.

### Task 8: The repository has both labels

- [ ] `gh label list` shows `request-ai-review` and `skip-ai-review`.
  - **Closed by:** the maintainer, before this plan's pull request merges.

### Task 9: A requested review counts toward merge

- [ ] After merge, adding `request-ai-review` to a reviewed pull request removes
  the label within the run, runs `Claude PR Review Responder`, and leaves
  `ai-review-present` from that `pull_request` run on the head commit, counted
  by `gh pr view --json statusCheckRollup`.
  - **Closed by:** the maintainer, on GitHub after merge.

### Task 10: The skip label behaves as decided

- [ ] After merge, a pull request created with
  `gh pr create --label skip-ai-review` runs no review on open, and the plan
  records whether the `opened` run's preflight saw the label.
- [ ] Adding `request-ai-review` to a pull request carrying `skip-ai-review`
  runs a review.
- [ ] Adding an unrelated label while a requested review is queued leaves that
  review queued.
  - **Closed by:** the maintainer, on GitHub after merge.

## Spec changes

[AI review gate](../spec/ai-review-gate.md):

``` markdown
## MODIFIED Requirements

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

## Requirement: a review runs on first push and on explicit request

The review job SHALL run when a pull request is opened, marked ready for review,
or reopened, on a push to a pull request that has no accepted review, and when
the `request-ai-review` label is added. The label SHALL run a review whether or
not an accepted review exists, and preflight SHALL remove it before authorizing
the request, so the label is on a pull request only until a run accepts or
rejects it. An assignment, a reviewer request, and a reviewer request's removal
SHALL NOT start a run. The review job SHALL NOT run
for a `pull_request` event on a draft pull request.

A `labeled` event for any other label SHALL NOT run a review and SHALL NOT share
the pull request's concurrency group, so it never replaces a queued review run.
Preflight does not run on a fork or bot-authored pull request, so a
`request-ai-review` label added there is not removed.

The workflow SHALL be triggered only by pull request, pull request review, and
merge group events: a comment, an issue, or a mention of `@claude` SHALL start
no run, and the workflow SHALL accept no `workflow_dispatch`.

The `ai-review-present` gate SHALL run for every pull request, pull request
review, and merge group event, a `labeled` event for any label included.

### Scenario: a draft is opened

- **WHEN** a pull request is opened as a draft
- **THEN** no review runs until the pull request is marked ready for review.

### Scenario: a writer requests a review with the label

- **WHEN** a writer adds `request-ai-review` to a reviewed pull request
- **THEN** preflight removes the label, a `pull_request` run reviews the pull
  request, and its `ai-review-present` reports that review.

### Scenario: a user without write access adds the label

- **WHEN** a user with triage but not write access adds `request-ai-review`
- **THEN** preflight removes the label and fails, and no review runs.

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

## Requirement: a pull request can opt out of the AI review run

A pull request carrying the `skip-ai-review` label SHALL skip the review
responder on open, ready for review, reopen, and push. An explicit
`request-ai-review` SHALL run a review whatever labels the pull request carries.
The label SHALL NOT waive the `ai-review-present` gate.

Preflight SHALL read the pull request's labels when it runs, not from the event
payload. A label added after a run's preflight read them does not apply to that
run.

The gate SHALL NOT read the label, because a job skipped by its own `if:`
satisfies a required status check, and a label the gate honoured would let
anyone who can label a pull request self-waive the mandatory review. A labelled
pull request with no accepted review keeps a red gate, and only a user with
ruleset bypass can merge it.

### Scenario: a labelled pull request triggers the workflow

- **WHEN** a pull request carrying `skip-ai-review` is opened or pushed to and
  no accepted review exists
- **THEN** no review responder runs, and `ai-review-present` runs and fails.

### Scenario: a labelled pull request already has an accepted review

- **WHEN** a pull request carrying `skip-ai-review` has an accepted review and
  receives a push
- **THEN** no review responder runs, and `ai-review-present` passes on the
  existing review.

### Scenario: a writer requests a review on a labelled pull request

- **WHEN** a writer adds `request-ai-review` to a pull request carrying
  `skip-ai-review`
- **THEN** a review runs, and `ai-review-present` reports it.

## REMOVED Requirements

### Requirement: a pull request review runs at a requested effort tier

Removed: every review sizes itself from the diff; no marker or label requests a
tier.
```

[AI review refresh](../spec/ai-review-refresh.md):

``` markdown
## MODIFIED Requirements

## Requirement: one AI review trigger per head commit

The catalog SHALL request an AI review only through `pr-request-ai-review`'s
`request-review.py`, and SHALL request it by adding the `request-ai-review`
label to the pull request. The catalog SHALL NOT change the pull request's
assignees to request a review, and SHALL NOT post an `@claude review` comment.

A review's input is the head commit together with the pull request's title and
description, which a review run reads when it starts. The script SHALL NOT add
the label while the pull request already carries it, or for a head commit that
an accepted AI review already names, submitted after the latest title or
description edit by a run that started after it, or that carries a
`Claude PR Review Responder` check run that is queued, in progress, or started
after that edit and completed with a conclusion other than `skipped` or
`cancelled`, whoever started it. A review submitted while a responder run that
started before the edit was running SHALL NOT count. When the pull request was
never edited, every such review and check counts. Accepted reviews are those the
AI review gate names, by author and state; a reaction names no commit and is not
counted.

A rationale, when given, SHALL be posted as a pull request comment that opens
with `AI review requested for <sha>:` and carries no `@claude` mention.

### Scenario: a second request for the same head

- **WHEN** a `Claude PR Review Responder` check on the head is queued, in
  progress, or started after the latest title or description edit and completed
  with a failure
- **THEN** the script adds no label and reports `ALREADY_REQUESTED` with that
  check's URL.

### Scenario: the label is already on the pull request

- **WHEN** the pull request carries `request-ai-review`
- **THEN** the script adds no label and reports `ALREADY_REQUESTED`.

### Scenario: the head is already reviewed

- **WHEN** an accepted AI review submitted after the latest title or description
  edit names the head commit
- **THEN** the script adds no label and reports `ALREADY_REVIEWED`.

### Scenario: the description changed after the head's review

- **WHEN** every completed responder check on the head started before the latest
  title or description edit, every accepted AI review naming the head was
  submitted before that edit or by one of those runs, and no responder check on
  the head is queued or in progress
- **THEN** the script adds `request-ai-review` and reports `SUCCESS`.

### Scenario: the description changed while a review was running

- **WHEN** the title or description is edited after a responder run on the head
  started, and that run finishes and submits its review after the edit
- **THEN** neither the run's check nor its review counts, and once no responder
  check is queued or in progress the script adds `request-ai-review` and reports
  `SUCCESS`.

### Scenario: a push to a reviewed pull request

- **WHEN** the only `Claude PR Review Responder` check on the head was skipped
- **THEN** the script adds `request-ai-review` and reports `SUCCESS`.

### Scenario: a request with a rationale

- **WHEN** the script adds the label with `--rationale`
- **THEN** it posts one comment opening `AI review requested for <sha>:` with
  the rationale, and no workflow run starts for it.

## Requirement: a requested review's status is read from the head commit's checks

The catalog SHALL judge a requested review as running when
`Claude PR Review Responder` or `ai-review-present` is pending on the pull
request's head commit, and as finished when the latest `ai-review-present` run
on the head completes, reading both from `gh pr checks`. It SHALL NOT look up
the review workflow by name or follow a run by id to decide either. When a
request produces no review check on the head, the cause SHALL be read from the
`pull_request` run of `ai-responder.yml` on the head branch, or from its
absence, and reported for a person rather than retried.

### Scenario: confirming a request

- **WHEN** the script adds the label and `Claude PR Review Responder` is pending
  on the head commit
- **THEN** the agent reports the review as started and waits on the head's
  checks instead of requesting again.

### Scenario: a request that reviewed nothing

- **WHEN** no review check runs on the head because adding the label started no
  `pull_request` run, or that run skipped or failed its preflight
- **THEN** the agent reports, respectively, a token whose events start no
  workflow, a bot-authored or fork pull request, or a requester without write
  access as needing a person, and requests no further review.
```

## Depends on

- [The AI responder posts as the plume-works-quill
  App](20261030-responder-quill-app-identity.md)

## Verification

- `uv run pre-commit run --files .github/workflows/ai-responder.yml .github/actions/run-claude-responder/action.yml`
  — `actionlint` and `zizmor` pass.
- `grep -nE "ci:skip-ai-review|ci:review-effort|REQUESTED REVIEW EFFORT|- assigned$|review_request" .github/workflows/ai-responder.yml .github/actions/run-claude-responder/action.yml .agents/plugins/agentdev/skills/pr-review/SKILL.md`
  finds nothing.
- `grep -niE "assignee|assignment|ci:skip-ai-review|ci:review-effort" .agents/plugins/agentdev/skills/pr-request-ai-review .agents/plugins/agentdev/skills/pr-merge/SKILL.md README.md docs/knowledge/data/features/ai-responder-workflows.md`
  finds nothing.
- `uv run pytest .agents/plugins/agentdev/tests/test_request_review.py` passes.
- `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
- Each inline `github-script` body in `ai-responder.yml` parses under
  `bun build --no-bundle`.
- `iwe normalize` and `iwe schema validate` pass.
- Tasks 9 and 10 are observed on GitHub after merge; Task 8 before it.

## Out of scope

- A repository-wide review pause for usage-quota outages.
- Settling whether auto-merge waits for a requested review; that question stays
  with [Verify that auto-merge waits for an assignee-triggered
  review](../backlog/verify-assignee-review-automerge.md).
- Revising [Resume interrupted Claude PR review
  sessions](20260909-resumable-claude-review-sessions.md) to build on this plan.
- Removing `request-ai-review` from fork or bot-authored pull requests.

## Key references

Verified anchor points (line numbers as of 2026-11-08):

- `.github/workflows/ai-responder.yml:10` — `pull_request` types
- `.github/workflows/ai-responder.yml:13` — `assigned`
- `.github/workflows/ai-responder.yml:16` — `review_requested` and
  `review_request_removed`
- `.github/workflows/ai-responder.yml:24` — concurrency group
- `.github/workflows/ai-responder.yml:44` — preflight `if:`
- `.github/workflows/ai-responder.yml:50` — preflight permissions
- `.github/workflows/ai-responder.yml:63` — `review_effort` output
- `.github/workflows/ai-responder.yml:98` — `[ci:skip-ai-review]` regex
- `.github/workflows/ai-responder.yml:100` — `[ci:review-effort=…]` regex
- `.github/workflows/ai-responder.yml:153` — `wantsReview`
- `.github/workflows/ai-responder.yml:160` — actions that always review
- `.github/workflows/ai-responder.yml:175` — `REQUESTED REVIEW EFFORT` prompt
- `.github/workflows/ai-responder.yml:230` — light-tier model override
- `.github/workflows/ai-responder.yml:239` — `ai-review-present` `if:`
- `.github/actions/run-claude-responder/action.yml:20` — `model` input
- `.github/actions/run-claude-responder/action.yml:98` — `MODEL` in "Compose
  Claude arguments"
- `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py:277`
  — author assignment lookup
- `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py:307`
  — assignee toggle
- `.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md:15` — "Post the
  request"
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:196` — "AI Review Recovery"
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:76` — "Effort Tiers"
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:385`
  — review refresh by assignment
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:444`
  — trigger behaviour bullets
- `README.md:348` — re-review instructions
- `docs/knowledge/data/features/ai-responder-workflows.md:78` — refresh by
  assignment
- `docs/knowledge/data/spec/ai-review-gate.md:109` — "a review runs on first
  push and on explicit request"
- `docs/knowledge/data/spec/ai-review-refresh.md:56` — "one AI review trigger
  per head commit"
