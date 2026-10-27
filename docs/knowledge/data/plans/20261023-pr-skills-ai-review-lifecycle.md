---
type: plan
created: 2026-10-23
release:
- bugs/pr-update-skips-review-eval
description: Make every push to a reviewed pull request run the re-review evaluation, request an AI review by toggling the pull request author's assignment at most once per head SHA through a bundled script, and retire the pr-* skill logic that assumed comment-requested reviews ran invisibly on the default branch, deleting pr-discover-ai-responder.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-27T08:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-sync/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-discover-ai-responder/SKILL.md
- resource: .github/workflows/ai-responder.yml
- resource: docs/knowledge/data/spec/ai-review-gate.md
- resource: docs/knowledge/data/architecture/assignee-review-trigger.md
---

# PR skills drive the AI review lifecycle on the single review workflow

## Context

Fixes [Bug: PR updates skip the re-review
evaluation](../bugs/pr-update-skips-review-eval.md). The [AI review
gate](../spec/ai-review-gate.md) passes on any accepted review across later
pushes and leaves refreshing it to the author; `pr-eval-review-needed` is the
skill that makes that call. Only `pr-feedback-resolution` invokes it, so
`pr-sync` — which keeps a pull request's title and body in step with what the
branch changes, and handles no feedback — and `pr-merge`'s CI-fix pushes update
reviewed pull requests without ever asking.

Absorbs [Simplify the pr-* skills for the single review
workflow](../backlog/simplify-pr-skills-single-review-workflow.md). Since [One
AI review workflow with a needs-coupled
gate](20260903-single-ai-review-workflow.md), every review runs in
`ai-responder.yml` and its `Claude PR Review Responder` and `ai-review-present`
checks are filed on the head commit, so `gh pr checks` shows the review while it
runs, and `ai-review-present` needs the review job, so it stays pending until
the review finishes and resolves in the same run. The plan removes the logic for
the earlier shape from `pr-merge`, `pr-request-ai-review`, and
`pr-discover-ai-responder`: workflow-filename discovery, run attribution by log
grep, watching runs by id, and the retired `Require AI Review` workflow name.

The maintainer decided that no consumer repository runs the earlier two-workflow
shape, so the skills are simplified outright with no shape detection, and that
`pr-discover-ai-responder` is deleted.

[Assignee-triggered AI re-reviews replace the comment
trigger](20261026-assignee-review-trigger.md) makes a `pull_request`/`assigned`
event the only way to request a re-review, and the bridge rejects an
`@claude review` comment. [Assignee-triggered AI
re-reviews](../architecture/assignee-review-trigger.md) records why. The
maintainer decided on 2026-10-27 that the catalog requests a review the same
way:

- the script removes and re-adds the pull request's author as assignee, and
  restores the assignees it found, so an author who was not assigned before is
  not assigned after;
- a `Claude PR Review Responder` check on the head commit is what shows that a
  review was already requested, because the run, not the assignment, is what
  reviews;
- a rationale, when given, is posted as a plain pull request comment.

## Approach

Four changes:

1. **Callers.** `pr-open` gains step 10, run on every update-mode run regardless
   of what the push or the body edit changed: apply `pr-eval-review-needed`.
   `pr-sync` inherits it unchanged. `pr-merge` step 5 applies the eval after a
   CI-fix push, before restarting its loop. `pr-feedback-resolution` already
   calls the eval and pushes through `push-branch.sh` rather than the `pr-open`
   skill, so it never evaluates twice.
2. **The test.** `pr-eval-review-needed` asks whether the diff since the newest
   reviewed commit goes beyond what the pull request's review threads and review
   comments since that review asked for. The evidence is read from the pull
   request, so a cold run from `pr-sync` or `pr-merge` decides on the same
   footing as a feedback pass. The request/decline lists are unchanged.
3. **One request per head, by assignment.** A new
   `pr-request-ai-review/agent-code/request-review.sh` is the only path that
   requests an AI review, used by `pr-request-ai-review` and by `pr-merge`'s AI
   Review Recovery, whose in-conversation ledger it replaces. It requests a
   review by toggling the author's assignment, which fires the
   `pull_request`/`assigned` event the responder reviews on. Before toggling, it
   reads the pull request's head, its reviews, and the head commit's
   `Claude PR Review Responder` check runs, and refuses when an accepted AI
   review already names the head or a responder check on the head shows a review
   was requested, whoever started it.
4. **The head commit's checks are the review's status.** A requested review has
   started when `Claude PR Review Responder` or `ai-review-present` is pending
   on the head commit, and it has finished when the latest `ai-review-present`
   run on the head completes; `pr-merge` and `pr-request-ai-review` watch
   `gh pr checks` for both and never look up the workflow by name or a run by
   id. A toggle that produces no review check on the head names its cause from
   the `pull_request` run it started on the head branch: a bot-authored or fork
   pull request, a requester without write access, or the `[ci:skip-ai-review]`
   marker — each needs a person, not a retry. `pr-discover-ai-responder`, its
   script, and its tests are deleted; every `Require AI Review` reference
   becomes `ai-review-present`.

`request-review.sh` takes `--pr <number>` (required), `--rationale <one line>`
(optional; a newline in it is a `PREFLIGHT_ERROR`), and `--repo <owner/repo>`
(optional). Accepted reviewers are the ones
[spec/ai-review-gate](../spec/ai-review-gate.md) names — `claude[bot]` and
`github-actions[bot]` — in state `APPROVED`, `CHANGES_REQUESTED`, or
`COMMENTED`. A `Claude PR Review Responder` check run on the head commit counts
as a request when it is queued or in progress, or completed with any conclusion
other than `skipped` or `cancelled`: a `skipped` responder is the gate-only run
that a push to a reviewed pull request starts, and doubt resolves toward
requesting, because a duplicate costs one redundant review while a wrongly
counted one leaves the head unreviewed. A completed responder that failed still
counts, so a failed review is reported, not retried on the same head.

The toggle: when the author is assigned, remove them, then add them back; when
they are not, add them, then remove them. Adding fires the event, and removing
fires none, because `unassigned` is not a trigger type. A rationale is posted
afterward as a comment whose body is
`AI review requested for <sha>: <rationale>`, which opens with no `@claude`
mention, so the bridge never dispatches it. The toggle and the comment need a
token whose events start workflows: an assignment made with an Actions
`GITHUB_TOKEN` starts no run. Output keys: `PR_NUMBER`, `HEAD_SHA`, `CHECK_URL`
(the existing responder check for `ALREADY_REQUESTED`; empty otherwise),
`COMMENT_URL` (the posted rationale; empty when none was posted), and the
`RESULT=` line:

| RESULT              | Exit | When                                                                    |
| ------------------- | ---- | ----------------------------------------------------------------------- |
| `SUCCESS`           | `0`  | The author's assignment was toggled for the head                        |
| `ALREADY_REVIEWED`  | `3`  | An accepted AI review's commit is the head                              |
| `ALREADY_REQUESTED` | `4`  | A `Claude PR Review Responder` check on the head counts as a request    |
| `PR_NOT_OPEN`       | `5`  | The pull request is closed, merged, or not found                        |
| `GH_UNAVAILABLE`    | `6`  | `gh` is missing, unauthenticated, or an API call failed, the toggle too |
| `PREFLIGHT_ERROR`   | `2`  | Missing `--pr`, unknown argument, multi-line rationale, no `jq`         |
| `SCRIPT_FAILURE`    | `1`  | Unhandled error                                                         |

Assumption, not decided by the maintainer: a failure on the toggle's second call
reports `GH_UNAVAILABLE` and names the assignment it could not restore, since
the review may already be running.

Rejected: posting `@claude review` — the bridge rejects it, and a dispatched
review's gate is not counted toward merge; posting a `review-head` marker
comment with each toggle — the responder check already names the head commit;
leaving a previously unassigned author assigned — the toggle would change who
the pull request visibly belongs to; hooking the eval into `pr-sync` alone —
`pr-open` reached directly in update mode would stay uncovered; gating step 10
on whether the push moved the head — a head pushed earlier by another path would
be skipped unevaluated; keeping `pr-discover-ai-responder` for the
toggle-without-check case — one
`gh run list --workflow ai-responder.yml --event pull_request` line in
`pr-request-ai-review` covers it, and the filename is fixed.

## Implementation Steps

### Task 1: Trigger script

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.sh`,
`.agents/plugins/agentdev/tests/test_request_review.py`

- [x] Tests, rewritten first with the stub `gh` on a hermetic `PATH`, fail
  against the comment-posting script and cover: no review and no responder check
  toggles an assigned author remove-then-add and an unassigned author
  add-then-remove, posts no comment without `--rationale`, and reports `SUCCESS`
  with an empty `COMMENT_URL`; `--rationale` posts one comment whose body is
  `AI review requested for <sha>: <rationale>` and prints its `COMMENT_URL`; no
  `@claude review` comment is posted on any path; an accepted review on the head
  toggles nothing (`ALREADY_REVIEWED`); an accepted review on an older commit
  still toggles; a review by an unaccepted author on the head, the Codex bot
  included, still toggles; a queued, in-progress, successful, or failed
  responder check on the head toggles nothing and prints its `CHECK_URL`
  (`ALREADY_REQUESTED`); a `skipped` or `cancelled` responder check on the head,
  or one on another commit, still toggles; a closed pull request
  (`PR_NOT_OPEN`); a failing `gh` call, and a failing second toggle call that
  names the assignment left unrestored (`GH_UNAVAILABLE`); missing `--pr` and a
  multi-line rationale (`PREFLIGHT_ERROR`); `RESULT=` is the last stdout line on
  every path
  - **Evidence:** commit "Request AI reviews by toggling the author's assignment
    in request-review.sh" — `tests/test_request_review.py` covers every listed
    case; against the comment-posting script 17 of its 27 tests failed, every
    toggle, responder-check, and Codex case among them.
- [x] `request-review.sh` implements the Approach's arguments, checks, toggle,
  rationale comment, output keys, and result table per
  `/agentdev:skill-scripts`, sourcing `bin/result-codes.sh`; it no longer reads
  check suites or issue comments or matches a `review-head` marker; `--help`
  lists options, keys, and results; `shellcheck -x` is clean; the tests pass
  - **Evidence:** commit "Request AI reviews by toggling the author's assignment
    in request-review.sh" —
    `uv run pytest .agents/plugins/agentdev/tests/test_request_review.py` — 27
    passed; `shellcheck -x` on `request-review.sh` is clean; a read-only
    `gh api` call on PR #485's head returned `name`, `status`, `conclusion`, and
    `html_url` on its check runs, the fields the script reads.

### Task 2: pr-request-ai-review requests through the script

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md`

- [x] The frontmatter `description` and the opening paragraph say the skill
  requests a review by toggling the author's assignment, not by posting a
  comment. `## Post the request` drops the `startsWith` explanation and the
  `@claude review` body, runs
  `agent-code/request-review.sh --pr <pr> [--rationale '<one line>']`, and maps
  each `RESULT` to its action (`ALREADY_REVIEWED` and `ALREADY_REQUESTED` are
  reported, not retried; `GH_UNAVAILABLE`, `PR_NOT_OPEN`, `PREFLIGHT_ERROR`,
  `SCRIPT_FAILURE` stop), naming `CHECK_URL` and `COMMENT_URL`. It says the
  toggle needs a token whose events start workflows.
  `## Post at most once per head SHA` states that the script counts a responder
  check on the head as the request, whoever started it, and that no skill
  requests a review any other way; the paragraphs on comment concurrency,
  editing, and deleting the trigger comment are removed
  - **Evidence:** commit "Request reviews by assignee toggle in
    pr-request-ai-review" — the description and opening name the toggle;
    `## Post the request` runs `request-review.sh` with a seven-row RESULT table
    naming `CHECK_URL` and `COMMENT_URL` and the `GITHUB_TOKEN` limit;
    `## Post at most once per head SHA` counts the responder check and drops the
    comment concurrency, editing, and deletion paragraphs;
    `validate_agent_files` reports 65/65 skills valid.

### Task 3: pr-request-ai-review confirms from the head commit's checks

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md`

- [x] `## Confirm it started` confirms the review from a pending
  `Claude PR Review Responder` or `ai-review-present` check on the head commit
  in `gh pr checks <pr>`, and drops workflow discovery and the claim that
  comment-triggered runs are not attached to the head
  - **Evidence:** `pr-request-ai-review/SKILL.md` `## Confirm it started` reads
    `gh pr checks <pr>` for a pending `Claude PR Review Responder` or
    `ai-review-present` check and no longer mentions workflow discovery or runs
    detached from the head.
- [x] Its gap shapes are read from the `pull_request` run of `ai-responder.yml`
  the toggle started on the head branch, found with
  `gh run list --workflow ai-responder.yml --event pull_request --branch <head>`:
  no run — the toggle's token starts no workflow, such as an Actions
  `GITHUB_TOKEN`; preflight skipped — its `if:` excluded a bot-authored or fork
  pull request, while `ai-review-present` still runs; preflight failed — the
  requester lacks write access; preflight passed, then the review job skipped —
  the `[ci:skip-ai-review]` marker; a review check that completes without a
  review — report the run's failure. The first four need a person. The section's
  opening says the toggle's `pull_request` run files its checks on the head
  commit, not that a trigger comment dispatches the responder
  - **Evidence:** commit "Confirm a toggled review from the head branch's
    pull_request run in pr-request-ai-review" — `## Confirm it started` opens on
    the toggle's `pull_request` run, reads it with
    `gh run list --event pull_request --branch`, and lists the five shapes;
    `grep` for `issue_comment` and `dispatch` on the skill returns nothing;
    `validate_agent_files` reports 0 errors.
- [x] `## Related Skills` drops `pr-discover-ai-responder`
  - **Evidence:** `grep -n discover` on `pr-request-ai-review/SKILL.md` returns
    nothing; `validate_agent_files` reports 63/63 skills valid.

### Task 4: The eval reads intent from the pull request

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md`

- [x] `## The test` asks whether the diff since the newest reviewed commit goes
  beyond what the pull request's review threads and review comments since that
  review asked for, replacing the first-person question; the request/decline
  lists in `## What counts as beyond the feedback` keep their items
  - **Evidence:** `pr-eval-review-needed/SKILL.md` `## The test` asks whether
    the diff since the newest reviewed commit goes beyond the review threads and
    comments since that review; `## What counts as beyond the feedback` is
    unchanged.
- [x] `## Establish what the last review saw` adds the command that reads the
  review threads and comments posted since the newest reviewed commit, and says
  that a run with no such threads judges the whole diff as undirected
  - **Evidence:** the section adds `gh pr view --json reviews,comments` and
    `gh api --paginate repos/{owner}/{repo}/pulls/<pr>/comments` filtered from
    the newest reviewed review, and judges the whole diff as new work when
    nothing since asks for anything; both commands return the expected fields
    against PR #429.
- [x] The frontmatter `description` and the opening paragraph name `pr-open`'s
  update mode and `pr-merge`'s CI-fix push as callers alongside feedback
  resolution
  - **Evidence:** the description and opening paragraph name `pr-open` update
    mode, `pr-merge` after a CI-fix push, and `pr-feedback-resolution`;
    `validate_agent_files` reports 63/63 skills valid.

### Task 5: pr-open evaluates on every update

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-open/SKILL.md`

- [x] A new `### 10. Re-Review Evaluation` follows step 9: in update mode,
  always apply [pr-eval-review-needed](../pr-eval-review-needed/SKILL.md) with
  `PR_NUMBER`, and add its decision to the step 9 report; create mode skips it.
  `### 10. Error Handling` becomes `### 11. Error Handling`
  - **Evidence:** `pr-open/SKILL.md` gains `### 10. Re-Review Evaluation`, run
    on every update-mode run and skipped in create mode, and renumbers
    `### 11. Error Handling`; `validate_agent_files` reports 63/63 skills valid.

### Task 6: pr-merge evaluates CI-fix pushes

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-merge/SKILL.md`

- [x] Step 5 applies [pr-eval-review-needed](../pr-eval-review-needed/SKILL.md)
  after the push and before restarting the loop
  - **Evidence:** `pr-merge/SKILL.md` step 5 applies `pr-eval-review-needed`
    after the push and before restarting the loop; `validate_agent_files`
    reports no errors.

### Task 7: pr-merge recovers the AI review from the head commit's checks

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-merge/SKILL.md`

- [x] Every `Require AI Review` reference — the completion criteria, the check
  classification in step 4, and the `## AI Review Recovery` introduction — names
  the `ai-review-present` check instead
  - **Evidence:** `pr-merge/SKILL.md` names `ai-review-present` in the
    completion criteria, step 4, and the `## AI Review Recovery` introduction;
    `grep -n "Require AI Review"` on it returns nothing.
- [x] `## AI Review Recovery` drops workflow-filename discovery, the
  in-conversation per-head-SHA ledger, the "`gh pr checks` is not sufficient"
  warning, the `Determine checkout ref` attribution, and `gh run watch` by run
  id. A review in progress is a pending `Claude PR Review Responder` or
  `ai-review-present` check on the head, waited on with `gh pr checks --watch`
  - **Evidence:** recovery steps 1-2 confirm the failed gate and wait on a
    pending `Claude PR Review Responder` or `ai-review-present` check with
    `gh pr checks --watch`; `grep` for `discover`, `ledger`, `gh run watch`, and
    `Determine checkout` on `pr-merge/SKILL.md` returns nothing.
- [x] Its trigger step requests the review through
  [pr-request-ai-review](../pr-request-ai-review/SKILL.md), whose script posts
  it; `ALREADY_REQUESTED` means wait on the head's checks, not post again
  - **Evidence:** recovery step 3 requests through `pr-request-ai-review` and
    handles `ALREADY_REQUESTED` by waiting on the head checks and
    `ALREADY_REVIEWED` by reporting.
- [x] The step that waits for a clean review's gate "to rerun and pass" says
  instead that the latest `ai-review-present` run on the head completes with the
  review, and a run whose review job ends without a review is reported, not
  retried; `## Related Skills` drops `pr-discover-ai-responder`
  - **Evidence:** recovery steps 4-6 wait for the latest `ai-review-present` run
    on the head and report a review job that ends without a review;
    `## Related Skills` lists `pr-request-ai-review` instead of
    `pr-discover-ai-responder`; `validate_agent_files` reports no errors.
- [x] The `## AI Review Recovery` introduction says the `ai-review-present`
  check accepts a submitted Claude review, without Codex, and that a review is
  requested by toggling the author's assignment, which runs the review in a
  `pull_request` run whose checks are filed on the head commit; no
  `@claude review` comment remains in `pr-merge/SKILL.md`
  - **Evidence:** commit "Name the assignee toggle in pr-merge's AI Review
    Recovery" — the introduction names a Claude review and the toggle's
    `pull_request` run; the completion criterion and recovery steps 3, 4, and 6
    drop Codex and the posted trigger; `grep -in '@claude\|codex'` on
    `pr-merge/SKILL.md` returns nothing; `validate_agent_files` reports 0
    errors.

### Task 8: Delete pr-discover-ai-responder

**Files:** Delete: `.agents/plugins/agentdev/skills/pr-discover-ai-responder/`
(`SKILL.md`, `agent-code/discover-ai-responder.sh`),
`.agents/plugins/agentdev/tests/test_discover_ai_responder.py`; Modify:
`.agents/plugins/agentdev/README.md`

- [x] The skill directory and its test file are removed, and the README's skills
  table drops its row
  - **Evidence:** `pr-discover-ai-responder/` and
    `tests/test_discover_ai_responder.py` are deleted and the README skills
    table drops the row; `uv run pytest .agents/plugins/agentdev/tests` — 206
    passed, 1 skipped; `validate_agent_files` reports 62/62 skills valid.
- [x] `grep -rn 'pr-discover-ai-responder\|discover-ai-responder\|Require AI Review' .agents`
  returns nothing
  - **Evidence:** the grep over `.agents` returns nothing (exit 1).

### Task 9: Codebase map

**Files:** Modify:
`docs/knowledge/data/codebase/agents/plugins/agentdev/skills.md` and any other
doc `stale-map-docs.py` reports

- [x] `/agentdev:iwe-map` refresh mode re-reads the docs `stale-map-docs.py`
  reports after Tasks 1-3 and 7, and the [agentdev
  tests](../codebase/agents/plugins/agentdev/tests.md) map describes
  `test_request_review.py` against the toggle; `stale-map-docs.py` reports none
  stale
  - **Evidence:** commit "map: refresh the agentdev tests map for the assignee
    toggle" — `codebase/agents/plugins/agentdev/tests` describes the toggle, the
    responder-check rule, and the half-done toggle; the catalog and skills maps
    are re-stamped; `stale-map-docs.py` ends `RESULT=SUCCESS`.

## Spec changes

[AI review refresh](../spec/ai-review-refresh.md):

``` markdown
## MODIFIED Requirements

## Requirement: one AI review trigger per head commit

The catalog SHALL request an AI review only through `pr-request-ai-review`'s
`request-review.sh`, and SHALL request it by toggling the pull request author's
assignment: an assigned author is removed and added back, and an unassigned
author is added and removed, so the assignees end as they were found. The
catalog SHALL NOT post an `@claude review` comment.

The script SHALL NOT toggle for a head commit that an accepted AI review already
names, or that carries a `Claude PR Review Responder` check run that is queued,
in progress, or completed with a conclusion other than `skipped` or
`cancelled`, whoever started it. Accepted reviews are those the AI review gate
names, by author and state; a reaction names no commit and is not counted.

A rationale, when given, SHALL be posted as a pull request comment that opens
with `AI review requested for <sha>:` and carries no `@claude` mention.

### Scenario: a second request for the same head

- **WHEN** a `Claude PR Review Responder` check on the head is queued, in
  progress, or completed with a failure
- **THEN** the script toggles nothing and reports `ALREADY_REQUESTED` with that
  check's URL.

### Scenario: the head is already reviewed

- **WHEN** an accepted AI review names the head commit
- **THEN** the script toggles nothing and reports `ALREADY_REVIEWED`.

### Scenario: a push to a reviewed pull request

- **WHEN** the only `Claude PR Review Responder` check on the head was skipped
- **THEN** the script toggles the author's assignment and reports `SUCCESS`.

### Scenario: an unassigned author

- **WHEN** the script requests a review on a pull request whose author is not
  assigned
- **THEN** it adds the author, then removes them, and the pull request ends
  with the assignees it had.

### Scenario: a request with a rationale

- **WHEN** the script toggles with `--rationale`
- **THEN** it posts one comment opening `AI review requested for <sha>:` with
  the rationale, and the bridge dispatches nothing for it.

## Requirement: a requested review's status is read from the head commit's checks

The catalog SHALL judge a requested review as running when
`Claude PR Review Responder` or `ai-review-present` is pending on the pull
request's head commit, and as finished when the latest `ai-review-present` run
on the head completes, reading both from `gh pr checks`. It SHALL NOT look up
the review workflow by name or follow a run by id to decide either. When a
toggle produces no review check on the head, the cause SHALL be read from the
`pull_request` run of `ai-responder.yml` on the head branch, or from its
absence, and reported for a person rather than retried.

### Scenario: confirming a request

- **WHEN** the script toggles the assignment and `Claude PR Review Responder` is
  pending on the head commit
- **THEN** the agent reports the review as started and waits on the head's
  checks instead of requesting again.

### Scenario: a toggle that reviewed nothing

- **WHEN** no review check runs on the head because the toggle started no
  `pull_request` run, or that run skipped or failed its preflight, or its
  preflight passed and its review job skipped
- **THEN** the agent reports, respectively, a token whose events start no
  workflow, a bot-authored or fork pull request, a requester without write
  access, or the `[ci:skip-ai-review]` marker as needing a person, and requests
  no further review.
```

## Verification

- `uv run pytest .agents/plugins/agentdev/tests/test_request_review.py` passes,
  and `uv run pytest .agents/plugins/agentdev/tests` stays green with
  `test_discover_ai_responder.py` gone.
- `shellcheck -x .agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.sh`
  is clean.
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes.
- `grep -rn '@claude review\|review-head\|chatgpt-codex-connector' .agents/plugins/agentdev/skills/pr-request-ai-review .agents/plugins/agentdev/skills/pr-merge .agents/plugins/agentdev/skills/pr-eval-review-needed .agents/plugins/agentdev/tests/test_request_review.py`
  returns only the bridge-rejection note in `pr-request-ai-review/SKILL.md` and
  test lines asserting that no `@claude` comment is posted or that a Codex
  review is not accepted.
- `grep -rn 'pr-discover-ai-responder\|Require AI Review\|gh run watch\|Determine checkout ref' .agents/plugins/agentdev`
  returns nothing.
- Manual, once [Assignee-triggered AI re-reviews replace the comment
  trigger](20261026-assignee-review-trigger.md) is on `main`: on a reviewed pull
  request whose author is not assigned, commit a behavior change no thread asked
  for and run `/agentdev:pr-sync`; the run reports a re-review decision, toggles
  the assignment, leaves the author unassigned, and confirms the review from a
  pending check on the head commit. Rerun `/agentdev:pr-sync` without a new
  commit; the script reports `ALREADY_REQUESTED` and toggles nothing.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- `update-branch`'s own pushes — it runs no eval after a base merge, though the
  eval counts a judgment-call conflict merge as new scope.
- Reading workflow runs, or looking a run up by id, inside `request-review.sh`;
  it reads the head commit's check runs only.
- Any change to the `ai-review-present` gate or the responder workflow, which
  [Assignee-triggered AI re-reviews replace the comment
  trigger](20261026-assignee-review-trigger.md) owns.
- A review dropped from the `pr-<n>` concurrency queue by a later pull request
  event, accepted by that plan's decision.
- A push during a running review: the new head's gate passes on the prior review
  while the older head's run is pending. The skills do not claim that watching
  `gh pr checks` closes this window.
- `pr-merge-stack`, which reaches review handling through `pr-merge`.

## Key references

Verified anchor points (line numbers as of 2026-10-27):

- `.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md:3` —
  frontmatter `description` naming the assignee toggle
- `.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md:15` —
  `## Post the request`, running `request-review.sh`
- `.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md:56` —
  `## Confirm it started`, causes read from the `pull_request` run
- `.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md:92` —
  `## Post at most once per head SHA`
- `.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md:110` —
  `## Related Skills`
- `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.sh:20`
  — `usage()`
- `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.sh:156`
  — accepted reviewers, Claude only
- `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.sh:162`
  — responder check runs on the head
- `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.sh:174`
  — the assignment toggle
- `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.sh:195`
  — the rationale comment body
- `.agents/plugins/agentdev/tests/test_request_review.py:29` — `GH_STUB`, the
  stub `gh` that logs write calls
- `.agents/plugins/agentdev/tests/test_request_review.py:96` — `pull_request()`
  and `make_fixture()` builders
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:242` —
  `## AI Review Recovery`
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:244` — introduction naming
  the assignee toggle
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:261` — step 3, request
  through `pr-request-ai-review`
- `.agents/plugins/agentdev/bin/result-codes.sh` — shared result helpers
- `.github/workflows/ai-responder.yml:82` — `preflight`, whose `if:` excludes
  bot-authored and fork `pull_request` events
- `.github/workflows/ai-responder.yml:267` — `assigned` among the actions that
  always review
- `.github/workflows/ai-responder.yml:502` — `ai-review-present`, needing
  `claude-respond`
- `docs/knowledge/data/codebase/agents/plugins/agentdev/skills.md:31` — family
  table
- `docs/knowledge/data/codebase/agents/plugins/agentdev/tests.md:1` — plugin
  tests map
