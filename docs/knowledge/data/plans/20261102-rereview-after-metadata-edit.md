---
type: plan
created: 2026-11-02
release:
- bugs/metadata-gate-review-blocks-rerequest
description: Let request-review.py request a fresh AI review of an already-reviewed head when the pull request's title or description changed after that head's review, so a metadata-gate stop is answered by fixing the description instead of pushing a commit.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-02T01:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py
- resource: .agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md
- resource: .agents/plugins/agentdev/tests/test_request_review.py
- resource: .github/actions/ai-review-status/action.yml
- resource: docs/knowledge/data/spec/ai-review-refresh.md
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
because the metadata gate reads them on every review. A head is therefore
covered only by AI reviews submitted, and responder checks completed, after the
latest title or description edit. Queued or in-progress responder checks still
count, whenever they started.

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
  - **Evidence:** commit c57256be;
    `uv run pytest .agents/plugins/agentdev/tests/test_request_review.py`
    against the unchanged script: the before-edit (body and title),
    completed-check and GraphQL-failure tests fail (4 failed); the after-edit
    and running-check guards pass, as their behavior already holds.
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
- [x] Every existing test keeps passing unchanged, with no edit times in the
  fixture.
  - **Evidence:** the same run at commit c57256be: every pre-existing test
    passed (30 passed, 4 failed — only the new ones).

### Task 3: Apply the cutoff in `request-review.py`

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py`

- [ ] Read the latest title or description edit time through `gh api graphql`,
  after the pull request is known to be open. A failed call returns
  `GH_UNAVAILABLE`.
- [ ] `reviewed()` counts only reviews whose `submitted_at` is after the cutoff;
  `requesting_check()` ignores completed checks whose `completed_at` is before
  the cutoff and keeps counting queued and in-progress ones.
- [ ] Update `USAGE` (the refusal paragraph and the `ALREADY_REVIEWED` and
  `ALREADY_REQUESTED` result lines) to name the edit cutoff.
- [ ] Task 2's tests and the whole
  `uv run pytest .agents/plugins/agentdev/tests` pass.

### Task 4: Document the rule in the skills

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md`,
`.agents/plugins/agentdev/skills/pr-merge/SKILL.md`

- [ ] `pr-request-ai-review`: the `ALREADY_REVIEWED` and `ALREADY_REQUESTED`
  rows say the review or check is newer than the last title or description edit,
  and the skill says that editing either is how a reviewed head gets another
  review.
- [ ] `pr-merge` Step 3: the script toggles at most once per head and title and
  description, not once per head SHA, and `ALREADY_REVIEWED` means a review
  newer than the last title or description edit names the head.
  `pr-feedback-resolution` already treats a gate body as feedback: update the
  title or description, then re-request review.
- [ ] `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.

### Task 5: Confirm the edit times on a live pull request

**Files:** none

- [ ] On an open pull request in this repository, read the GraphQL query
  `request-review.py` uses before and after editing the description and before
  and after renaming the title, and confirm each edit moves the cutoff past the
  newest AI review.

## Spec changes

[AI review refresh](../spec/ai-review-refresh.md):

``` markdown
## MODIFIED Requirements

## Requirement: one AI review trigger per head commit

The catalog SHALL request an AI review only through `pr-request-ai-review`'s
`request-review.py`, and SHALL request it by toggling the pull request author's
assignment: an assigned author is removed and added back, and an unassigned
author is added and removed, so the assignees end as they were found. The
catalog SHALL NOT post an `@claude review` comment.

A review's input is the head commit together with the pull request's title and
description. The script SHALL NOT toggle for a head commit that an accepted AI
review submitted after the latest title or description edit already names, or
that carries a `Claude PR Review Responder` check run that is queued, in
progress, or completed after that edit with a conclusion other than `skipped`
or `cancelled`, whoever started it. When the pull request was never edited,
every such review and check counts. Accepted reviews are those the AI review
gate names, by author and state; a reaction names no commit and is not counted.

A rationale, when given, SHALL be posted as a pull request comment that opens
with `AI review requested for <sha>:` and carries no `@claude` mention.

### Scenario: a second request for the same head

- **WHEN** a `Claude PR Review Responder` check on the head is queued, in
  progress, or completed with a failure after the latest title or description
  edit
- **THEN** the script toggles nothing and reports `ALREADY_REQUESTED` with that
  check's URL.

### Scenario: the head is already reviewed

- **WHEN** an accepted AI review submitted after the latest title or
  description edit names the head commit
- **THEN** the script toggles nothing and reports `ALREADY_REVIEWED`.

### Scenario: the description changed after the head's review

- **WHEN** every accepted AI review naming the head, and every completed
  responder check on it, predates the latest title or description edit, and no
  responder check on the head is queued or in progress
- **THEN** the script toggles the author's assignment and reports `SUCCESS`.

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

## Out of scope

- The `ai-review-present` gate and its acceptance rule ([AI review
  gate](../spec/ai-review-gate.md)) — unchanged.
- Starting a review automatically on a description edit (`pull_request: edited`
  in `ai-responder.yml`); requesting stays an explicit toggle.
- Marking a review as a metadata-gate stop, or changing `pr-review`'s gate.

## Key references

Verified anchor points (line numbers as of 2026-11-02):

- `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py:33`
  — `USAGE`; `:132` — `reviewed`; `:142` — `requesting_check`; `:162` — `run`;
  `:211` — the `ALREADY_REVIEWED` return; `:219` — the `ALREADY_REQUESTED`
  return
- `.agents/plugins/agentdev/tests/test_request_review.py:29` — `GH_STUB`; `:250`
  — `test_accepted_review_on_head_toggles_nothing`; `:291` —
  `test_responder_check_on_head_counts_as_request`
- `.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md:34` — the
  `ALREADY_REVIEWED` row
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:230` — "at most once per
  head SHA"; `:234` — the `ALREADY_REVIEWED` handling in Step 3
- `.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md:123` — a
  metadata-gate body is feedback: update the description, re-request review
- `docs/knowledge/data/spec/ai-review-refresh.md:45` — Requirement: one AI
  review trigger per head commit
- `.github/actions/ai-review-status/action.yml:69` — the gate's accepted states,
  which include `changes_requested`
