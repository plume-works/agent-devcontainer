---
type: plan
created: 2026-11-08
release:
- features/ai-responder-workflows
description: Request an AI re-review with a request-ai-review label and block every AI review with a block-ai-reviews label, replacing the assignee trigger, the [ci:skip-ai-review] body marker, and the [ci:review-effort=…] tiers.
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/run-claude-responder/action.yml
- resource: .agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: openspec/specs/ai-review-gate/spec.md
- resource: openspec/specs/ai-review-gate/spec.md
- resource: openspec/specs/ai-review-refresh/spec.md
completed: 2026-11-08
stage: done
---

# AI reviews are requested and skipped with labels

## Context

Changes [AI responder workflows](../features/ai-responder-workflows.md).

Before this plan, a re-review was requested by removing the pull request's
author as assignee and adding them back ([Assignee-triggered AI
re-reviews](../../../../openspec/specs/ai-review-gate/spec.md#rationale)). The
maintainer's goal is an easy, trusted, explicit way to request a re-review.

A label applied to a pull request fires `pull_request`/`labeled`, a
`pull_request` event like `assigned`, so its run is counted by the `main`
ruleset and the pull request's status rollup, and its checks land on the head
commit.

The maintainer decided on 2026-11-08:

- a `request-ai-review` label is the one way to request a review; the label is
  on the pull request from the moment someone adds it until a review of it
  finishes, and the review job removes it as `plume-works-quill` once Claude
  finishes, never when the review is cancelled, so a push that cancels a
  requested review leaves the request for the push's run;
- `assigned` no longer requests a review, so an assignee means ownership only;
- `review_requested` and `review_request_removed` are not triggers: neither
  requests a review, so a run they started would review nothing;
- a `block-ai-reviews` label replaces the `[ci:skip-ai-review]` body marker;
  while it is on, no AI review runs, explicit requests included, and a
  `request-ai-review` added meanwhile stays on the pull request; removing
  `block-ai-reviews` starts a run that reviews a waiting request;
- `request-review.py` adds `request-ai-review` to a blocked pull request, so the
  request waits visibly, and reports `BLOCKED`, unless the input is already
  reviewed or requested;
- the `[ci:review-effort=light|full]` marker and requested effort tiers are
  removed; every review sizes itself;
- every run in the pull request's `pr-<n>` concurrency group takes a
  `request-ai-review` it finds, so a request whose own run was cancelled while
  pending is taken by the run that replaced it, and `request-review.py` re-sends
  a label that no unfinished run is left to take; a request on a draft or from
  someone without write access stays until a later run reviews it;
- this plan lands before [Resume interrupted Claude PR review
  sessions](20260909-resumable-claude-review-sessions.md), which is revised
  afterwards to build on the `labeled` trigger and concurrency split this plan
  adds.

A `block-ai-reviews` label saves the review runs that would fail while Claude is
unavailable. It does not let a pull request merge without ruleset bypass,
because `ai-review-present` still requires an accepted review.

## Approach

```
 add request-ai-review ──► pull_request/labeled ──► concurrency pr-<n>
                                                     │
 add any other label ────► pull_request/labeled ──► concurrency label-<run id>
                                                     │
  preflight ── reads current labels from the API (GITHUB_TOKEN, read-only)
            ├── wantsReview: block-ai-reviews on            → no (request label kept)
          │                request-ai-review in pr-<n>   → yes
          │                opened/ready/reopened/push*   → yes
          │                anything else                 → no
          ▼
  claude-respond (if wantsReview) ── mint App token ── Claude review
          └── removes request-ai-review unless cancelled ──► ai-review-present

 * push only while no accepted review exists
```

`ai-responder.yml` adds `labeled` and `unlabeled` and drops `assigned`,
`review_requested`, and `review_request_removed` from its `pull_request` types.
The workflow-level concurrency group sends every label event to a group of its
own, keyed by run id, except adding `request-ai-review` and removing
`block-ai-reviews`, which join `pr-<n>`, so an unrelated label change never
replaces a review queued in `pr-<n>`. `ai-review-present` keeps running in those
runs and evaluates the existing reviews: a job skipped by its own `if:`
satisfies a required check, so skipping the gate for an unrelated label would
let anyone with triage access turn it green.

Every run in `pr-<n>` takes a `request-ai-review` it finds on the pull request:
preflight reviews when it is present, and `run-claude-responder` removes it with
the minted App token after the Claude step, whether the review succeeded or
failed, so the timeline shows `plume-works-quill` removing it. It never removes
it when the review is cancelled: a push that cancels a requested review leaves
the label, and the push's run reviews the new head and removes it. A failed
review removes the label, so it is not retried on every later push. A request
whose own run was cancelled while pending in `pr-<n>`, because a later event
replaced it there, is taken by the replacing run. A run that does not review
leaves the label for a later run: on a draft, it waits for ready-for-review;
from someone without write access, it waits for a writer's run; while
`block-ai-reviews` is on, it waits for the label's removal, whose run reviews
it. A run started by another label leaves `request-ai-review` in place.
Preflight reads the pull request's labels from the API rather than the event
payload, so a `block-ai-reviews` label added right after the pull request was
created is seen by the `opened` run whenever it lands before preflight reads it.

The effort marker, the `review_effort` output, the light-tier model override,
and `run-claude-responder`'s `model` input are removed. `pr-review` keeps its
internal effort matrix for self-sizing and loses only the requested-tier route.

`request-review.py` requests a review by adding `request-ai-review`. When the
label is already on the pull request, it reports `ALREADY_REQUESTED` while a run
of `ai-responder.yml` on the head branch is unfinished, since a run in `pr-<n>`
will take the label; with no unfinished run, the label is stale, and the script
removes and re-adds it, which fires a new `labeled` event. Every catalog skill,
the specs, the feature doc, the README, and the consumption guide follow. A new
architecture note supersedes `assignee-review-trigger` and
`pr-review-effort-tiers`, which are left unedited.

Known limits:

- A run started by an unrelated label evaluates the gate on the existing
  reviews, so while a requested review is still running, that run's gate can
  report a result the pending review later replaces.
- Preflight does not run on fork or bot-authored pull requests, so a
  `request-ai-review` added there stays until someone removes it; no review can
  run on them either way.
- An `opened` run whose preflight reads the labels before a creation-time
  `block-ai-reviews` lands still reviews.
- A request run cancelled before its review job finishes leaves
  `request-ai-review` on the pull request until the next run in `pr-<n>` takes
  it or `request-review.py` re-sends it; a person re-adding the label sends
  nothing.
- A request from someone without write access stays on the pull request, and the
  next run a writer starts in `pr-<n>` reviews it.
- An unfinished run started by another label also makes `request-review.py`
  report `ALREADY_REQUESTED`; the next call after it finishes re-sends the
  label.

Rejected alternatives:

- **Keep the assignee toggle**: it borrows a field that means ownership, and
  takes two actions per request.
- **A comment trigger**: a comment-started run is not a `pull_request` run, so
  its gate does not count toward merge, and it requires parsing free-form
  comments.
- **A persistent `ai-review-requested` state label removed after the review
  posts**: a failed review leaves the label on, and it must be removed by hand
  before the next request.
- **A skip label that an explicit request overrides**: a label named for
  skipping reviews that still lets a request through reads as broken, so the
  label blocks every review and a waiting request runs once it is removed.
- **Labels for the effort tier**: every review sizes itself.
- **A repository-wide review pause**: a per-PR `block-ai-reviews` label covers a
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
  `synchronize`, `labeled`, and `unlabeled`.
  - **Evidence:** commit 95c6732d; `on.pull_request.types` lists `opened`,
    `reopened`, `ready_for_review`, `synchronize`, `labeled`, `unlabeled`;
    actionlint passes.
- [x] The concurrency group of every label event is unique to its run, except
  adding `request-ai-review` and removing `block-ai-reviews`, which keep
  `pr-<n>` like every other `pull_request` event.
  - **Evidence:** commit 95c6732d; the group expression sends a `labeled` or
    `unlabeled` event to `label-<run id>` unless it adds `request-ai-review` or
    removes `block-ai-reviews`; actionlint and zizmor pass.

### Task 2: Preflight honours the two labels

**Files:** Modify: `.github/workflows/ai-responder.yml`,
`.github/actions/run-claude-responder/action.yml`

- [x] Preflight does not remove `request-ai-review`, and its `GITHUB_TOKEN`
  holds `pull-requests: read`.
  - **Evidence:** commit 3306a331; preflight has no label-removal step and holds
    `contents: read`, `issues: read`, `pull-requests: read`; actionlint and
    zizmor pass.
- [x] `run-claude-responder` removes `request-ai-review` with the minted App
  token after the Claude step, unless the job was cancelled, when
  `claude-respond` passes it the label preflight found; a label another run
  already removed is not an error.
  - **Evidence:** commit 4d5ccbc8; "Take the review request label" runs after
    "Claude Responder" when `remove-request-label` is `true`, the Claude step
    finished with `success` or `failure`, and the job is not cancelled; it
    deletes the label with the App token and treats `HTTP 404` as taken by
    another run; the step passes shellcheck, and zizmor passes.
- [x] Preflight reads the pull request's current labels from the API.
  - **Evidence:** commit ebfe8ab4; "Determine checkout ref" pages
    `github.rest.issues.listLabelsOnIssue` for the pull request; actionlint
    passes.
- [x] `wantsReview` is true when the pull request carries `request-ai-review`
  and not `block-ai-reviews`, for a run in `pr-<n>`, and false for a label event
  outside `pr-<n>`.
  - **Evidence:** commit 95c6732d; `wantsReview` returns false outside `pr-<n>`
    or when `BLOCK_AI_REVIEWS` is set, then true when `REQUEST_LABEL` is set;
    every inline script parses under `bun build --no-bundle`.
- [x] `block-ai-reviews` on the pull request makes `wantsReview` false for every
  event, a waiting `request-ai-review` included, and leaves that label in place;
  the `[ci:skip-ai-review]` body regex is removed.
  - **Evidence:** commit 95c6732d; "Determine checkout ref" sets
    `blockAiReviews` from the live labels, `wantsReview` returns false whenever
    it is set, before the request check, and no step removes `request-ai-review`
    in that case; the `[ci:skip-ai-review]` regex is gone; every inline script
    parses under `bun build --no-bundle`.
- [x] Removing `block-ai-reviews` starts a run in `pr-<n>` that reviews when
  `request-ai-review` is on the pull request.
  - **Evidence:** commit 95c6732d; `unlabeled` is a `pull_request` type,
    removing `block-ai-reviews` keeps `pr-<n>`, and `wantsReview` returns true
    for it when `request-ai-review` is present; actionlint passes.
- [x] `ai-review-present` runs for every `labeled` and `unlabeled` event.
  - **Evidence:** commit 95c6732d; the gate's `if:` is `always()` for every
    `pull_request` event, and both label actions are `pull_request` types;
    actionlint passes.

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
- [x] With `request-ai-review` already on the pull request, it reports
  `ALREADY_REQUESTED` while a run of `ai-responder.yml` on the head branch is
  unfinished, and otherwise removes and re-adds the label and reports `SUCCESS`.
  - **Evidence:** commit 34f6546e; with the label present, `run()` lists
    `ai-responder.yml` runs on the head branch, returns `ALREADY_REQUESTED`
    while one is unfinished, and otherwise DELETEs and re-POSTs the label before
    reporting `SUCCESS`; the three stale-label tests pass.
- [x] Tests cover a present label with an unfinished run, a stale label being
  removed and re-added, and a failing removal.
  - **Evidence:** commit 34f6546e;
    `test_label_waiting_for_a_run_is_already_requested`,
    `test_stale_label_is_removed_and_added_again`, and
    `test_failing_stale_label_removal_is_gh_unavailable` pass among the 40.
- [x] Tests cover the label being added, the label already present, and that no
  assignee call is made.
  - **Evidence:** commit 34f6546e;
    `uv run pytest .agents/plugins/agentdev/tests/test_request_review.py` passes
    40 tests, including `test_request_adds_the_label`,
    `test_label_waiting_for_a_run_is_already_requested`, and
    `test_assignees_are_never_touched`.
- [x] With `block-ai-reviews` on the pull request, it adds `request-ai-review`
  unless already present and reports `BLOCKED`, with a test.
  - **Evidence:** commits e359da43 and 79d47811; `run()` reports
    `ALREADY_REVIEWED` or `ALREADY_REQUESTED` first, then on a blocked pull
    request POSTs `request-ai-review` unless present and returns `BLOCKED` (7);
    `test_blocked_pull_request_queues_the_request`,
    `test_blocked_pull_request_with_waiting_request_adds_nothing`, and
    `test_blocked_pull_request_already_reviewed_queues_nothing` pass among 43.
- [x] `SKILL.md` describes the label request, the re-sent stale label, the
  `BLOCKED` result, and its confirmation.
  - **Evidence:** commit e359da43; "Post the request" describes the block, the
    result table lists `BLOCKED`, and "Confirm it started" names
    `block-ai-reviews` among the reasons a label stays; `validate_agent_files`
    reports 0 errors.

### Task 5: Merge and evaluation skills follow the label

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-merge/SKILL.md`

- [x] `## AI Review Recovery` describes requesting with `request-ai-review`,
  treats an added label, a started run, or a pending review as not yet complete,
  and reports `BLOCKED` for a person instead of waiting.
  - **Evidence:** commit 98da9a59; step 3 reports `BLOCKED` as a merge blocker
    for a person and stops waiting; the rest of the recovery requests with
    `request-ai-review`.

### Task 6: Consumer docs describe the labels

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`,
`README.md`, `docs/knowledge/data/features/ai-responder-workflows.md`

- [x] The consumption guide adds creating the `request-ai-review` and
  `block-ai-reviews` labels to the required prerequisites and describes
  requesting and blocking reviews with them.
  - **Evidence:** commit 3dd70bd5; prerequisite 3 creates `request-ai-review`
    and `block-ai-reviews` and describes both, and the trigger bullets and
    Workflow B summary match; `validate_agent_files` reports 0 errors.
- [x] `README.md` says to add `request-ai-review` to request another review and
  `block-ai-reviews` to stop every review.
  - **Evidence:** commit 3dd70bd5; "Pull-request automation" says to add
    `request-ai-review` and that `block-ai-reviews` stops every review, and
    lists both labels among the prerequisites; prettier passes.
- [x] The feature's `## Behaviour` describes both labels, drops the assignee
  trigger, the body markers, and requested tiers, and links the new note.
  - **Evidence:** commit 3dd70bd5; `## Behaviour` describes `request-ai-review`
    and "Pull requests can block every review, not the gate.", and links
    `architecture/label-review-triggers`; `iwe schema validate` passes.
- [x] `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
  - **Evidence:** commit ba52ceed;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    reports 0 errors and 0 warnings.

### Task 7: Architecture note records the label triggers

**Files:** Create: `docs/knowledge/data/architecture/label-review-triggers.md`;
Modify: `docs/knowledge/data/architecture.md`

- [x] The note records the decisions under `## Context`, the routing under
  `## Approach`, its known limits, and every rejected alternative, and states
  that it supersedes [Assignee-triggered AI
  re-reviews](../../../../openspec/specs/ai-review-gate/spec.md#rationale) and
  [PR review effort
  tiers](../../../../openspec/specs/ai-review-gate/spec.md#rationale), which are
  left unedited.
  - **Evidence:** commit 38389c9b; `architecture/label-review-triggers` carries
    the decisions under `## Context`, the routing under `## Approach`,
    `## Known limits`, all five rejected alternatives, and the line superseding
    `assignee-review-trigger` and `pr-review-effort-tiers`, which the commit
    leaves unchanged; `iwe schema validate` passes.
- [x] The note says a run in `pr-<n>` takes a `request-ai-review` left by a
  cancelled request run, that the review job removes it as `plume-works-quill`,
  that `block-ai-reviews` holds every review and its removal runs a waiting
  request, and that `request-review.py` re-sends a stale label, and lists the
  remaining cases among its known limits.
  - **Evidence:** commit e90b55ff; `architecture/label-review-triggers` records
    the block, the unblock run, removal after the review, the pickup, and the
    stale-label re-send, and its known limits and rejected alternatives match
    the plan; `iwe schema validate` passes.
- [x] The note is linked from `data/architecture.md`.
  - **Evidence:** commit 38389c9b; `data/architecture.md` inclusion-links
    `architecture/label-review-triggers` in key order, before
    `manual-stacked-prs`; `iwe schema validate` passes.

### Task 8: The repository has both labels

- [x] `gh label list` shows `request-ai-review` and `block-ai-reviews`, and no
  `skip-ai-review`.
  - **Closed by:** the maintainer, before this plan's pull request merges.
  - **Evidence:** repository settings, observed 2026-11-08: `skip-ai-review` was
    renamed to `block-ai-reviews` with the maintainer's approval;
    `gh label list` shows `request-ai-review` and `block-ai-reviews` and no
    `skip-ai-review`.

### Task 9: A requested review counts toward merge

- [x] On a pull request running this plan's workflow, adding `request-ai-review`
  to a reviewed pull request has `plume-works-quill` remove the label within the
  run, runs `Claude PR Review Responder`, and leaves `ai-review-present` from
  that `pull_request` run on the head commit, counted by
  `gh pr view --json statusCheckRollup`.
  - **Closed by:** the maintainer, on a pull request running this workflow.
  - **Evidence:** pull request #758 at 076e9610: the waiting `request-ai-review`
    was reviewed by run 42460733010, whose review job removed the label as
    `plume-works-quill[bot]` at 07:57:39 after the 07:57:32 review, and whose
    `ai-review-present` passed; `gh pr view 758 --json statusCheckRollup` listed
    `ai-review-present` as `SUCCESS`.

### Task 10: The block label and the queue behave as decided

- [x] A pull request running this plan's workflow and created with
  `gh pr create --label block-ai-reviews` runs no review on open.
  - **Evidence:** pull request #763 at 5b38ff87, created with
    `--label block-ai-reviews`: runs 42461972700 and 42461972665 both skipped
    `Claude PR Review Responder`, no review was posted, and the label stayed on.
- [x] Adding `request-ai-review` to a pull request carrying `block-ai-reviews`
  runs no review and leaves the request label on.
  - **Evidence:** pull request #758 at 076e9610, carrying `block-ai-reviews`:
    `request-ai-review` added at 07:54:22 started run 42460672914, which skipped
    `Claude PR Review Responder`, and the label stayed on the pull request.
- [x] Removing `block-ai-reviews` from that pull request runs the waiting
  review, whose job then removes `request-ai-review`.
  - **Evidence:** pull request #758 at 076e9610: removing `block-ai-reviews` at
    07:55:17 started run 42460733010, which ran `Claude PR Review Responder`;
    `plume-works-quill[bot]` posted its review at 07:57:32 and removed
    `request-ai-review` at 07:57:39.
- [x] Adding an unrelated label while a requested review is queued leaves that
  review queued.
  - **Evidence:** pull request #752: with `request-ai-review` run 42453979498
    reviewing and request run 42454017435 pending in `pr-752`, adding
    `documentation` started run 42454039608, which ran preflight and
    `ai-review-present` without a review and finished while 42454017435 stayed
    pending.
- [x] A push during a requested review re-reviews: the cancelled review leaves
  `request-ai-review`, and the push's run reviews the new head and removes it.
  - **Evidence:** pull request #758: the push of 5fe15e9c at 08:12 cancelled
    request run 42461809176 before its review started, `request-ai-review`
    (added at 07:59:00) stayed on, and the push's run 42461906440 reviewed
    5fe15e9c at 08:18:21; `plume-works-quill[bot]` removed `request-ai-review`
    at 08:18:29.
- [x] A push queued behind a pending `request-ai-review` run takes the request:
  its review job removes the label and reviews.
  - **Closed by:** the maintainer, on a pull request running this workflow.
  - **Evidence:** pull request #752: with run 42455065884 reviewing and request
    run 42455169059 pending in `pr-752`, the push of e572ef51 started run
    42455195990, which cancelled both, took `request-ai-review` (removed by
    `plume-works-quill[bot]` at 06:34:39), ran `Claude PR Review Responder`, and
    passed `ai-review-present` with the 06:36:14 approval.

## Spec changes

[AI review gate](../../../../openspec/specs/ai-review-gate/spec.md):

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
not an accepted review exists. Every run in the pull request's concurrency group
SHALL take a `request-ai-review` it finds on the pull request: the run SHALL
review when the request is authorized and the pull request is not a draft, and
while the pull request carries no `block-ai-reviews`, and the review job SHALL
remove the label with the reviewer App's token once the review finishes, whether it succeeded or failed, and SHALL NOT remove it when
the review is cancelled. A request whose own run was cancelled while pending is
therefore taken by the run that replaced it. A run that does not review SHALL
leave the label for a later run in that group, as SHALL a run started by another
label. A cancelled review therefore leaves the label until the next run in that
group takes it, or until `request-review.py` re-sends it. An assignment, a
reviewer request, and a reviewer request's removal SHALL NOT start a run. The
review job SHALL NOT run for a `pull_request` event on a draft pull request.

Removing `block-ai-reviews` SHALL start a run in the pull request's concurrency
group, which takes a waiting `request-ai-review`. Every other label event, adding
or removing any other label, SHALL NOT run a review and SHALL NOT share the pull
request's concurrency group, so it never replaces a queued review run.
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

- **WHEN** `request-ai-review` is added while another run of the pull request
  is in progress, and a push queues before the request's run starts
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
for it, whatever event starts the run, an explicit `request-ai-review`
included. A `request-ai-review` added while the block is on SHALL stay on the
pull request, and removing `block-ai-reviews` SHALL start a run that reviews it.
The label SHALL NOT waive the `ai-review-present` gate.

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

## REMOVED Requirements

### Requirement: a pull request review runs at a requested effort tier

Removed: every review sizes itself from the diff; no marker or label requests a
tier.

### Requirement: a pull request can opt out of the AI review run

Removed: replaced by "a pull request can block every AI review"; the
`[ci:skip-ai-review]` body marker and its scenarios are gone.
```

[AI review refresh](../../../../openspec/specs/ai-review-refresh/spec.md):

``` markdown
## MODIFIED Requirements

## Requirement: one AI review trigger per head commit

The catalog SHALL request an AI review only through `pr-request-ai-review`'s
`request-review.py`, and SHALL request it by adding the `request-ai-review`
label to the pull request. The catalog SHALL NOT change the pull request's
assignees to request a review, and SHALL NOT post an `@claude review` comment.

While the pull request carries `block-ai-reviews`, the script SHALL first
report `ALREADY_REVIEWED` or `ALREADY_REQUESTED` where the rules below find the
input reviewed or a responder check requesting it; otherwise it SHALL add
`request-ai-review` unless it is already present, and SHALL report `BLOCKED`,
because no review can run until the block is lifted.

A review's input is the head commit together with the pull request's title and
description, which a review run reads when it starts. While the pull request
already carries the label and is not blocked, the script SHALL NOT add it
when a run of `ai-responder.yml` on the head branch is unfinished, because a run in the pull
request's concurrency group takes the label; with no unfinished run the label
is stale, and the script SHALL remove it and add it again. The script SHALL NOT
add the label for a head commit that
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

### Scenario: the label is waiting for a run

- **WHEN** the pull request carries `request-ai-review`, does not carry
  `block-ai-reviews`, and a run of `ai-responder.yml` on the head branch is
  unfinished
- **THEN** the script adds no label and reports `ALREADY_REQUESTED`.

### Scenario: the pull request is blocked

- **WHEN** the pull request carries `block-ai-reviews`, and no accepted review
  or responder check covers its input
- **THEN** the script adds `request-ai-review` unless it is already present, and
  reports `BLOCKED`.

### Scenario: a blocked pull request that is already reviewed

- **WHEN** the pull request carries `block-ai-reviews`, and an accepted AI
  review already names its head after the latest title or description edit
- **THEN** the script adds no label and reports `ALREADY_REVIEWED`, so lifting
  the block does not review the same input again.

### Scenario: the label is stale

- **WHEN** the pull request carries `request-ai-review` and no run of
  `ai-responder.yml` on the head branch is unfinished
- **THEN** the script removes the label, adds it again, and reports `SUCCESS`.

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
- `grep -nE "skip-ai-review|ci:review-effort|REQUESTED REVIEW EFFORT|- assigned$|review_request" .github/workflows/ai-responder.yml .github/actions/run-claude-responder/action.yml .agents/plugins/agentdev/skills/pr-review/SKILL.md`
  finds nothing.
- `grep -rniE "assignee|assignment|skip-ai-review|ci:review-effort" .agents/plugins/agentdev/skills/pr-request-ai-review .agents/plugins/agentdev/skills/pr-merge/SKILL.md .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md README.md docs/knowledge/data/features/ai-responder-workflows.md`
  finds nothing.
- `uv run pytest .agents/plugins/agentdev/tests/test_request_review.py` passes.
- `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
- Each inline `github-script` body in `ai-responder.yml` parses under
  `bun build --no-bundle`.
- `iwe normalize` and `iwe schema validate` pass.
- Tasks 9 and 10 are observed on GitHub on pull requests running this plan's
  workflow; Task 8 before merge.

## Verification results

- A `skip-ai-review` label added by `gh pr create --label` one second after the
  pull request was created was seen by the `opened` run's preflight: the run
  skipped the review (pull request #753).

## Out of scope

- A repository-wide review pause for usage-quota outages.
- Settling whether auto-merge waits for a requested review; that question stays
  with [Verify that auto-merge waits for an assignee-triggered
  review](../backlog/verify-assignee-review-automerge.md).
- Revising [Resume interrupted Claude PR review
  sessions](20260909-resumable-claude-review-sessions.md) to build on this plan.
- Removing `request-ai-review` from fork or bot-authored pull requests.

## Key references

- `.github/workflows/ai-responder.yml#on.pull_request.types` — `unlabeled` among
  the `pull_request` types
- `.github/workflows/ai-responder.yml#concurrency` — concurrency group with the
  `label-<run id>` branch
- `.github/workflows/ai-responder.yml#jobs.preflight` — preflight job and its
  label-event condition
- `.github/workflows/ai-responder.yml › "core.setOutput('blockAiReviews', labels.some((label) =>"`
  — `blockAiReviews` from the live labels
- `.github/workflows/ai-responder.yml › "const wantsReview = (() =>"` —
  `wantsReview`
- `.github/workflows/ai-responder.yml › "remove-request-label: $"` —
  `claude-respond` passes the request label
- `.github/workflows/ai-responder.yml#jobs.ai-review-present` —
  `ai-review-present`
- `.github/actions/run-claude-responder/action.yml#inputs.remove-request-label`
  — `remove-request-label` input
- `.github/actions/run-claude-responder/action.yml › "name: Take the review request label"`
  — "Take the review request label" after the Claude step
- `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py::BLOCK_LABEL`
  — `BLOCK_LABEL`
- `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py::run`
  — `BLOCKED` path
- `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py::run`
  — stale-label check
- `.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md#post-the-request`
  — "Post the request"
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md#ai-review-recovery` — "AI
  Review Recovery"
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md#effort-tiers` — "Effort
  Tiers"
- `README.md#pull-request-automation › "To request another review after new work lands, add the"`
  — re-review instructions
- `docs/knowledge/data/spec/ai-review-gate.md#requirement-a-review-runs-on-first-push-and-on-explicit-request`
  — "a review runs on first push and on explicit request"
- `docs/knowledge/data/spec/ai-review-gate.md#requirement-a-pull-request-can-opt-out-of-the-ai-review-run`
  — "a pull request can opt out of the AI review run"
- `docs/knowledge/data/spec/ai-review-refresh.md#requirement-one-ai-review-trigger-per-head-commit`
  — "one AI review trigger per head commit"
