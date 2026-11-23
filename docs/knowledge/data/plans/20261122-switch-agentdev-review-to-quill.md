---
type: plan
created: 2026-11-22
release: internal
description: Replace this repository's AI responder workflow with quill-as-a-service in one change, make the required approval the only review gate, and point the catalog's review skills at the Quill Review check.
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py
---

# Switch this repository's AI review to quill-as-a-service

## Context

[Build quill-as-a-service](20261122-quill-as-a-service.md) builds the service
and proves it on `plume-works/images`. The user's decision: "Once it's ready we
switch agentdev in one go." Until then this repository keeps
`.github/workflows/ai-responder.yml`, its two actions, the `plume-works-review`
environment, and the required `ai-review-present` check.

The catalog's review skills assume the workflow: `request-review.py` reads the
runs of `ai-responder.yml` and the `Claude PR Review Responder` check, and
`pr-merge` and `pr-eval-review-needed` describe `ai-review-present` as the gate.

## Approach

One change removes the workflow, its actions, its CI hooks, and the cost scripts
that read its runs. The `main` ruleset keeps its required approval and drops the
`ai-review-present` check
([ADR-0102](../adr/0102-required-approval-is-the-only-ai-review-gate.md)), and
the service configuration lists this repository
([ADR-0101](../adr/0101-ai-review-runs-in-quill-as-a-service.md)).

`request-review.py` keeps its results and its rule of one request per head and
title and description, and reads the `Quill Review` check run where it read the
responder check. A `Quill Review` check on the head that is queued or in
progress means the label waits for a running review; with none, a label still on
the pull request is stale. The skills describe the service's rules
([ADR-0103](../adr/0103-review-starts-on-open-or-request.md)): no required
review check, Quill's approval counting toward the required approval, and
`request-ai-review` held until the review ends.

The backlog tasks about the workflow's tests, its silent review runs, and its
assignee trigger end with it and are cancelled.

## Implementation Steps

### Task 1: Remove the workflow and its actions

**Files:** Delete: `.github/workflows/ai-responder.yml`,
`.github/actions/run-claude-responder/action.yml`,
`.github/actions/ai-review-status/action.yml`,
`.github/actions/ai-review-status/review-gate.js`,
`.github/actions/ai-review-status/review-gate.test.js`; Modify:
`.github/workflows/ci.yml`

- [ ] The workflow and both action directories are gone.
- [ ] `.github/workflows/ci.yml` names neither `ai-review-status` in its path
  filters nor `bun test ./.github/actions/ai-review-status`.

### Task 2: Remove the responder cost scripts

**Files:** Delete: `scripts/download-claude-responder-runs.py`,
`scripts/analyze-claude-responder-costs.py`,
`scripts/tests/test_download_claude_responder_runs.py`

- [ ] The three files are gone.
- [ ] `uv run pytest scripts/tests` passes.

### Task 3: Read the Quill Review check in request-review.py

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py`,
`.agents/plugins/agentdev/tests/test_request_review.py`

- [ ] A label on the pull request with a queued or in-progress `Quill Review`
  check on the head reports `ALREADY_REQUESTED`;
  `test_label_waiting_for_a_quill_review_is_already_requested` passes.
- [ ] A label on the pull request with no unfinished `Quill Review` check on the
  head is removed and added again; `test_stale_label_is_removed_and_added_again`
  passes.
- [ ] A `Quill Review` check on the head that started after the latest title or
  description edit and completed other than cancelled reports
  `ALREADY_REQUESTED`;
  `test_quill_review_check_completed_after_metadata_edit_counts` passes.
- [ ] The script reads no workflow runs.
- [ ] Every test in `.agents/plugins/agentdev/tests/test_request_review.py`
  passes.

### Task 4: Describe the service in pr-request-ai-review

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md`

- [ ] `## Confirm it started` confirms the request by a queued or in-progress
  `Quill Review` check on the head and names no workflow, `gh run`, or
  `ai-review-present`.
- [ ] `## Post the request` names the service as the reviewer and no longer asks
  for a token whose events start workflows.

### Task 5: Make the required approval the merge gate in pr-merge

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-merge/SKILL.md`

- [ ] `## Completion Criteria` and `## AI Review Recovery` name the required
  approval and the `Quill Review` check, and no longer name `ai-review-present`
  or `Claude PR Review Responder`.

### Task 6: Update pr-eval-review-needed

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md`

- [ ] `## Why this decision has an owner` and
  `## Establish what the last review saw` describe Quill's latest verdict and
  the required approval, and name no `ai-review-present` gate.

### Task 7: Update the README

**Files:** Modify: `README.md`

- [ ] `## Pull-request automation` describes quill-as-a-service and names no
  `ai-responder.yml`, `plume-works-review` environment, or secret.

### Task 8: Cancel the backlog tasks the workflow carried

**Files:** Modify: `docs/knowledge/data/backlog.md`; Move:
`docs/knowledge/data/backlog/test-responder-workflow-js.md`,
`docs/knowledge/data/backlog/fail-review-run-without-review.md`,
`docs/knowledge/data/backlog/verify-assignee-review-automerge.md`

- [ ] The three tasks are at `stage: cancelled` under
  `data/archive/next-release/backlog/`.
- [ ] `iwe schema validate` passes.

### Task 9: Point the service at this repository

**Closed by:** a maintainer adding `plume-works/agent-devcontainer` to the
service configuration, when this plan's pull request merges.

- [ ] The service configuration lists `plume-works/agent-devcontainer`.

### Task 10: Drop the review check from the ruleset

**Closed by:** a repository administrator, when this plan's pull request merges.

- [ ] The `main` ruleset requires one approval and no `ai-review-present` check.

### Task 11: Delete the review environment

**Closed by:** a repository administrator, after Task 10.

- [ ] The `plume-works-review` environment and its secrets are gone.

### Task 12: Observe a review by the service

**Closed by:** the first pull request opened on this repository after Task 9.

- [ ] It gets a review by `plume-works-quill[bot]`.
- [ ] It gets a `Quill Review` check on its head.
- [ ] No Actions run of `ai-responder.yml` starts for it.

## Acceptance

### Scenario: A request waiting for a running review is not sent again

- **WHEN** `request-review.py` runs on a pull request that carries
  `request-ai-review` and has a queued or in-progress `Quill Review` check on
  its head
- **THEN** it reports `ALREADY_REQUESTED` and changes no label
- **Test:**
  `.agents/plugins/agentdev/tests/test_request_review.py::test_label_waiting_for_a_quill_review_is_already_requested`

### Scenario: A stale request label is sent again

- **WHEN** `request-review.py` runs on a pull request that carries
  `request-ai-review` and has no unfinished `Quill Review` check on its head
- **THEN** it removes the label and adds it again
- **Test:**
  `.agents/plugins/agentdev/tests/test_request_review.py::test_stale_label_is_removed_and_added_again`

### Scenario: The Quill Review check on the head counts as a request

- **WHEN** a `Quill Review` check on the head started after the latest title or
  description edit and completed other than cancelled
- **THEN** `request-review.py` reports `ALREADY_REQUESTED` with that check's URL
- **Test:**
  `.agents/plugins/agentdev/tests/test_request_review.py::test_quill_review_check_completed_after_metadata_edit_counts`

### Scenario: The merge needs an approval, not a review check

- **WHEN** a pull request on this repository is ready to merge
- **THEN** the `main` ruleset asks for one approval, which Quill's approval
  satisfies, and no `ai-review-present` check
- **Checked at ship:**
  `.agents/plugins/agentdev/skills/pr-merge/SKILL.md#completion-criteria`

### Scenario: The service reviews this repository's pull requests

- **WHEN** a pull request opens on this repository
- **THEN** quill-as-a-service reviews it, and no `ai-responder.yml` run starts
- **Checked at ship:** `.github/workflows/`, which holds no `ai-responder.yml`

## ADRs

[The AI review of this repository runs in
quill-as-a-service](../adr/0101-ai-review-runs-in-quill-as-a-service.md)

[The required approval is the only gate of the AI
review](../adr/0102-required-approval-is-the-only-ai-review-gate.md)

[A review starts on open or on
request](../adr/0103-review-starts-on-open-or-request.md)

## Depends on

[Build quill-as-a-service](20261122-quill-as-a-service.md)

## Verification

``` bash
uv run pytest .agents/plugins/agentdev/tests/test_request_review.py scripts/tests
uv run validate_agent_files --recommend . --require-marketplace claude
test ! -e .github/workflows/ai-responder.yml
test ! -e .github/actions/run-claude-responder
test ! -e .github/actions/ai-review-status
rg -n 'ai-review-present|ai-responder\.yml|Claude PR Review Responder|plume-works-review' \
  .github/workflows/ci.yml README.md \
  .agents/plugins/agentdev/skills/pr-request-ai-review \
  .agents/plugins/agentdev/skills/pr-merge/SKILL.md \
  .agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md
iwe schema validate
```

The `rg` command prints nothing.

## Out of scope

- Building the service and onboarding `plume-works/images`; [Build
  quill-as-a-service](20261122-quill-as-a-service.md) holds it.
- Other repositories that copied the workflow from the template.
- The archived documents and findings that describe the workflow.

## Key references

- `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py::run`
  › "actions/workflows/ai-responder.yml/runs" — the workflow-run read that Task
  3 replaces.
- `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py::requesting_check`
  — the check that counts as a request.
- `.agents/plugins/agentdev/tests/test_request_review.py::test_label_waiting_for_a_run_is_already_requested`
  — the test that Task 3 replaces.
- `.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md#confirm-it-started`
  — the confirmation through workflow runs.
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md#ai-review-recovery` — the
  recovery of a red `ai-review-present`.
- `.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md#why-this-decision-has-an-owner`
  — the gate the skill explains.
- `README.md#pull-request-automation` — the workflow's description.
- `.github/workflows/ci.yml` › "bun test ./.github/actions/ai-review-status" —
  the CI step that tests the gate module.
