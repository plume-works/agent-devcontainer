---
type: plan
created: 2026-11-02
release:
- bugs/metadata-gate-review-blocks-rerequest
description: Let request-review.py request a fresh AI review of an already-reviewed head when the pull request's title or description changed after that head's review, so a metadata-gate stop is answered by fixing the description instead of pushing a commit.
sources:
- resource: .agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py
- resource: .agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md
- resource: .agents/plugins/agentdev/tests/test_request_review.py
- resource: .github/actions/ai-review-status/action.yml
- resource: openspec/specs/ai-review-refresh/spec.md
stage: done
completed: 2026-11-02
released: 2.1.0
---

# Re-request an AI review after a title or description edit

## Context

Fixes [Bug: a metadata-gate review blocks the re-review it asks
for](../bugs/metadata-gate-review-blocks-rerequest.md).

The metadata gate stops a review with `REQUEST_CHANGES` when the title or
description is stale. After the author fixes them, `request-review.py` refuses
the re-request, because that review names the head. Under the one-approval
`main` ruleset the pull request then cannot merge without a new commit. The
gate's review satisfies `ai-review-present`, so the block is the missing
approval, not a red check.

Two guards in `request-review.py` both refuse: `reviewed()` on the gate's
review, and `requesting_check()` on the gate run's completed, successful
`Claude PR Review Responder` check on the head.

## Approach

A review's input is the head commit together with the title and description,
because the metadata gate reads them on every review, once, when its run starts.
A head is therefore covered only by responder runs started after the latest
title or description edit, and by the AI reviews they submit: a review submitted
while a run that started before the edit was running does not count. Queued or
in-progress responder checks still count, whenever they started.

The script reads the latest edit time from GitHub through one GraphQL query:
`PullRequest.lastEditedAt` for the description, and the newest
`RENAMED_TITLE_EVENT` in `timelineItems` for the title. A pull request never
edited has no cutoff: every accepted review naming the head and every counting
responder check still refuses the request.

The rule applies to every AI review, not only to gate stops. A full review also
runs the gate, so the reviewer saw different input, and each extra review needs
an edit, so the rule cannot loop by itself. No review is marked as a gate stop.

Rejected: a hash of the title and description stored in the gate's review body.
The hash precisely ignores a revert to the reviewed text, but it needs a review
body format, a computation in `pr-review`, and a text-normalization rule.
Comparing timestamps changes only `request-review.py`, and its worst case is one
extra review. An override argument on the script was rejected too: it moves the
per-head guard to the caller's judgment.

Assumption: an edit that changes no text is not recorded as an edit. If GitHub
records one, that edit allows a re-review. That costs one review and needs no
handling.

## Implementation Steps

### Task 1: Correct the bug's symptom

**Files:** Modify:
`docs/knowledge/data/bugs/metadata-gate-review-blocks-rerequest.md`

- [x] Replace the Symptom's claim that `ai-review-present` stays red: the gate's
  `REQUEST_CHANGES` review satisfies `ai-review-present`, and the pull request
  cannot merge because the one-approval `main` ruleset gets no approval. Add to
  Root cause that `requesting_check()` also refuses, on the gate run's completed
  responder check.
  - **Evidence:** commit 1759c194 rewrites the Symptom and Root cause;
    `iwe schema validate` passed in that commit's pre-commit run.

### Task 2: Failing tests for the edit cutoff

**Files:** Modify: `.agents/plugins/agentdev/tests/test_request_review.py`

- [x] Teach `GH_STUB` to answer `api graphql` with a fixture's `lastEditedAt`
  and title-rename times (both absent by default), and give `review()` and
  `check_run()` a `submitted_at` / `completed_at`.
  - **Evidence:** commit c57256be adds the `graphql` branch and `-F` handling to
    `GH_STUB`, the `edits` and `fail_graphql` fixture keys, and `submitted_at` /
    `completed_at` on `review()` and `check_run()`.
- [x] Add tests that fail against the current script:
  - an accepted review on the head submitted before a description edit →
    `SUCCESS`, toggled;
  - an accepted review on the head submitted before a title rename → `SUCCESS`;
  - an accepted review on the head submitted after the latest edit →
    `ALREADY_REVIEWED`;
  - a completed responder check on the head that finished before the edit, with
    the head's review also older → `SUCCESS`;
  - a queued or in-progress responder check that started before the edit →
    `ALREADY_REQUESTED`;
  - a failing GraphQL call → `GH_UNAVAILABLE`, nothing toggled.
  - **Evidence:** commit c57256be;
    `uv run pytest .agents/plugins/agentdev/tests/test_request_review.py`
    against the unchanged script: the before-edit (body and title),
    completed-check and GraphQL-failure tests fail (4 failed); the after-edit
    and running-check guards pass, as their behavior already holds. Commit
    e0b8ccc3 adds `test_responder_check_completed_after_metadata_edit_counts`;
    408 passed, 15 skipped.
- [x] Every existing test keeps passing unchanged, with no edit times in the
  fixture.
  - **Evidence:** the same run at commit c57256be: every pre-existing test
    passed; all 4 failures were new tests.

### Task 3: Apply the cutoff in `request-review.py`

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py`

- [x] Read the latest title or description edit time through `gh api graphql`,
  after the pull request is known to be open. A failed call returns
  `GH_UNAVAILABLE`.
  - **Evidence:** commit e667e133 adds `edit_times()` (one `gh api graphql`
    query) after the open check; a failed or malformed response returns
    `GH_UNAVAILABLE`, covered by
    `test_failing_edit_time_query_is_gh_unavailable`.
- [x] `reviewed()` counts only reviews whose `submitted_at` is after the cutoff;
  `requesting_check()` ignores completed checks whose `completed_at` is before
  the cutoff and keeps counting queued and in-progress ones.
  - **Evidence:** commit e667e133: `reviewed()` and `requesting_check()` take
    the cutoff through `after()`; covered by the Task 2 before-edit, after-edit,
    completed-check and running-check tests.
- [x] Update `USAGE` (the refusal paragraph and the `ALREADY_REVIEWED` and
  `ALREADY_REQUESTED` result lines) to name the edit cutoff.
  - **Evidence:** commit e667e133 rewrites the refusal paragraph and the
    `ALREADY_REVIEWED` / `ALREADY_REQUESTED` lines of `USAGE`;
    `test_help_lists_options_keys_and_results` passes.
- [x] Task 2's tests and the whole
  `uv run pytest .agents/plugins/agentdev/tests` pass.
  - **Evidence:** at commit e667e133:
    `uv run pytest .agents/plugins/agentdev/tests/test_request_review.py` 34
    passed, and `uv run pytest .agents/plugins/agentdev/tests` 407 passed, 15
    skipped.

### Task 4: Document the rule in the skills

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md`,
`.agents/plugins/agentdev/skills/pr-merge/SKILL.md`

- [x] `pr-request-ai-review`: the `ALREADY_REVIEWED` and `ALREADY_REQUESTED`
  rows say the review or check is newer than the last title or description edit,
  and the skill says that editing either is how a reviewed head gets another
  review.
  - **Evidence:** commit d2bedf5e: `pr-request-ai-review/SKILL.md` adds the
    edit-cutoff paragraph under Post the request and rewrites the
    `ALREADY_REVIEWED` and `ALREADY_REQUESTED` rows; commit e0b8ccc3 rewrites
    `## Post at most once per reviewed input` to match.
- [x] `pr-merge` Step 3: the script toggles at most once per head and title and
  description, not once per head SHA, and `ALREADY_REVIEWED` means a review
  newer than the last title or description edit names the head.
  `pr-feedback-resolution` already treats a gate body as feedback: update the
  title or description, then re-request review.
  - **Evidence:** commit d2bedf5e: `pr-merge/SKILL.md` Step 3 says once per head
    and title and description, and `ALREADY_REVIEWED` names a review newer than
    the last edit; commit e0b8ccc3 fixes the same wording under Related Skills.
- [x] `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
  - **Evidence:** at commit d2bedf5e:
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    reported 64/64 skills valid, 0 errors, 0 warnings.

### Task 5: Confirm the edit times on a live pull request

**Files:** none

- [x] On an open pull request in this repository, read the GraphQL query
  `request-review.py` uses before and after editing the description and before
  and after renaming the title, and confirm each edit moves the cutoff past the
  newest AI review.
  - **Evidence:** `edit_times()` at commit e667e133, run against #587 (newest AI
    review 2026-10-31T17:16:09Z): no edits gave no cutoff; a description edit
    set it to 2026-11-02T01:03:21Z; a title rename then moved it to 01:03:23Z
    without changing `lastEditedAt`. Both edits were reverted, and they stay in
    #587's edit history and timeline.

## Spec changes

[AI review refresh](../../../../openspec/specs/ai-review-refresh/spec.md):

``` markdown
## MODIFIED Requirements

## Requirement: one AI review trigger per head commit

The catalog SHALL request an AI review only through `pr-request-ai-review`'s
`request-review.py`, and SHALL request it by toggling the pull request author's
assignment: an assigned author is removed and added back, and an unassigned
author is added and removed, so the assignees end as they were found. The
catalog SHALL NOT post an `@claude review` comment.

A review's input is the head commit together with the pull request's title and
description, which a review run reads when it starts. The script SHALL NOT
toggle for a head commit that an accepted AI review already names, submitted
after the latest title or description edit by a run that started after it, or
that carries a `Claude PR Review Responder` check run that is queued, in
progress, or started after that edit and completed with a conclusion other than
`skipped` or `cancelled`, whoever started it. A review submitted while a
responder run that started before the edit was running SHALL NOT count. When the
pull request was never edited, every such review and check counts. Accepted
reviews are those the AI review gate names, by author and state; a reaction
names no commit and is not counted.

A rationale, when given, SHALL be posted as a pull request comment that opens
with `AI review requested for <sha>:` and carries no `@claude` mention.

### Scenario: a second request for the same head

- **WHEN** a `Claude PR Review Responder` check on the head is queued, in
  progress, or started after the latest title or description edit and completed
  with a failure
- **THEN** the script toggles nothing and reports `ALREADY_REQUESTED` with that
  check's URL.

### Scenario: the head is already reviewed

- **WHEN** an accepted AI review submitted after the latest title or description
  edit names the head commit
- **THEN** the script toggles nothing and reports `ALREADY_REVIEWED`.

### Scenario: the description changed after the head's review

- **WHEN** every completed responder check on the head started before the latest
  title or description edit, every accepted AI review naming the head was
  submitted before that edit or by one of those runs, and no responder check on
  the head is queued or in progress
- **THEN** the script toggles the author's assignment and reports `SUCCESS`.

### Scenario: the description changed while a review was running

- **WHEN** the title or description is edited after a responder run on the head
  started, and that run finishes and submits its review after the edit
- **THEN** neither the run's check nor its review counts, and once no responder
  check is queued or in progress the script toggles the author's assignment and
  reports `SUCCESS`.

### Scenario: a push to a reviewed pull request

- **WHEN** the only `Claude PR Review Responder` check on the head was skipped
- **THEN** the script toggles the author's assignment and reports `SUCCESS`.

### Scenario: an unassigned author

- **WHEN** the script requests a review on a pull request whose author is not
  assigned
- **THEN** it adds the author, then removes them, and the pull request ends with
  the assignees it had.

### Scenario: a request with a rationale

- **WHEN** the script toggles with `--rationale`
- **THEN** it posts one comment opening `AI review requested for <sha>:` with
  the rationale, and the bridge dispatches nothing for it.
```

## Verification

- `uv run pytest .agents/plugins/agentdev/tests/test_request_review.py` — the
  Task 2 tests fail before Task 3 and pass after it.
- `uv run pytest .agents/plugins/agentdev/tests` passes.
- `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
- Task 5's live check confirms both edit kinds move the cutoff.
- `iwe normalize` and `iwe schema validate` pass.

## Verification results

- The AI review of the pull request found that judging a responder check by its
  completion time counted a run that started before an edit and finished after
  it, so that edit never got a review. The rule now judges a run by its start
  time and discounts the reviews such a run submits; the Approach and the spec
  delta state it (commit 80d0d014,
  `test_review_from_a_run_started_before_the_edit_does_not_count`).

## Out of scope

- The `ai-review-present` gate and its acceptance rule ([AI review
  gate](../../../../openspec/specs/ai-review-gate/spec.md)) — unchanged.
- Starting a review automatically on a description edit (`pull_request: edited`
  in `ai-responder.yml`); requesting stays an explicit toggle.
- Marking a review as a metadata-gate stop, or changing `pr-review`'s gate.

## Key references

- `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py::RESPONDER`
  — `USAGE`;
  `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py::fetch_list`
  — `reviewed`;
  `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py::finish`
  — `requesting_check`;
  `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py::edit_times`
  — `run`;
  `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py::reviewed`
  — the `ALREADY_REVIEWED` return;
  `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py::requesting_check`
  — the `ALREADY_REQUESTED` return
- `.agents/plugins/agentdev/tests/test_request_review.py::STARTED_AT` —
  `GH_STUB`;
  `.agents/plugins/agentdev/tests/test_request_review.py::test_assigned_author_is_removed_then_added_back`
  — `test_accepted_review_on_head_toggles_nothing`;
  `.agents/plugins/agentdev/tests/test_request_review.py::test_accepted_review_on_head_toggles_nothing`
  — `test_responder_check_on_head_counts_as_request`
- `.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md#post-the-request`
  — the `ALREADY_REVIEWED` row
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md#ai-review-recovery › "toggles the author's assignment at most once per head"`
  — "at most once per head SHA";
  `.agents/plugins/agentdev/skills/pr-merge/SKILL.md#ai-review-recovery › "accepted review newer than the last title or description"`
  — the `ALREADY_REVIEWED` handling in Step 3
- `.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md#workflow-1-collect-all-feedback-sources › "stops before its inline passes when the PR"`
  — a metadata-gate body is feedback: update the description, re-request review
- `docs/knowledge/data/spec/ai-review-refresh.md#requirement-one-ai-review-trigger-per-head-commit`
  — Requirement: one AI review trigger per head commit
- `.github/actions/ai-review-status/action.yml#runs.steps.Evaluate AI review acceptance.with.script`
  — the gate's accepted states, which include `changes_requested`
