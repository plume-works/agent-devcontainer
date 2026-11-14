---
type: plan
created: 2026-11-13
release: internal
description: Move the decision logic of the AI review gate and of the image promotion out of the workflow files into scripts, and add a test that runs each decision.
sources:
- resource: docs/spec-audit/requirements.jsonl
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/docker/promote/action.yml
---

# Test the decisions that the workflows make

## Context

[The spec usefulness audit](../findings/spec-usefulness-audit.md) found five
behaviours that only a spec states and that are inline code in a workflow file.
Four are in `spec/ai-review-gate` and one is in `spec/image-pinning`. Each one
decides a merge or a publish, and nothing runs it before GitHub does.

The test rules in `AGENTS.md#tests` permit only a test that runs the behaviour.
A test cannot run code that is a string in a YAML file.

This plan is a part of [Shrink the knowledge base to an issue tracker and
decision records](../backlog/shrink-knowledge-base-to-issues-and-adrs.md). It is
a separate plan because a mistake in it shows only on a real pull request or a
real publish.

## Approach

Each decision moves to a script that the workflow step calls. The script gets
its inputs as arguments or environment variables and prints its decision. The
workflow keeps the calls to GitHub. A test runs the script with inputs that the
test controls.

The move changes no behaviour. Two observation tasks confirm that on GitHub.

## Implementation Steps

### Task 1: Move and test the decisions of the AI review gate

**Files:** Create: a script and a test file for the decisions; Modify:
`.github/workflows/ai-responder.yml`

Each test shows what the `fate_note` of its row in
`docs/spec-audit/requirements.jsonl` says.

- [x] A test runs "PRs are blocked until an AI review exists".
  - **Evidence:** `scripts/tests/test_ai_review_gate_decide.py` runs the
    `review-accepted` and `gate` decisions of
    `.github/actions/ai-review-gate/decide.py`; 48 tests pass.
- [x] A test runs "the responder only acts for authorized same-repository
  requests".
  - **Evidence:** the same test file runs the `is-fork` and `authorize`
    decisions for each permission level and head repository.
- [x] A test runs "a review runs on first push and on explicit request".
  - **Evidence:** the same test file runs the `wants-review` decision for each
    pull request action, label event, draft, and label state.
- [x] A test runs "trusted-bot pull requests are approved without an AI review".
  - **Evidence:** the same test file runs the `trusted-bot` and `bot-approval`
    decisions for foreign commits, foreign pushes, and a reused branch.
- [x] `.github/workflows/ai-responder.yml` calls the script for each of the four
  decisions and holds no copy of them in a step. The `concurrency:` group and
  the `if:` of each job stay, because GitHub evaluates them before a step runs.
  - **Evidence:** each step decision and the acceptance rule in
    `.github/actions/ai-review-status/action.yml` call
    `.github/actions/ai-review-gate`; zizmor and actionlint pass.

### Task 2: Move and test the decision of the image promotion

**Files:** Create: a script and a test file for the decision; Modify:
`.github/actions/docker/promote/action.yml`

- [x] A test runs "published tags name only tested images" for a descendant
  commit, for an unknown commit, and for an image that has no label.
  - **Evidence:** `scripts/tests/test_promote_tag_decision.py` runs
    `.github/actions/docker/promote/tag-decision.sh` in a fixture repository for
    these cases and for an ancestor and the same commit; 5 tests pass.
- [x] `.github/actions/docker/promote/action.yml` calls the script and holds no
  copy of the decision.
  - **Evidence:** the tag loop calls `tag-decision.sh` and keeps only the
    registry calls; shellcheck, zizmor, and actionlint pass.

### Task 3: Observe the AI review gate on a pull request

**Closed by:** the first pull request that is opened after this change is on the
default branch.

- [ ] The gate blocks the pull request before the AI review exists.
- [ ] The gate passes after the AI review is submitted.

### Task 4: Observe an image promotion

**Closed by:** the first image build on the default branch after this change.

- [ ] The promotion step publishes the tag of the tested image.

## Acceptance

None — no behavioral change

## Depends on

[Add ADRs and take the workflow off
specs](../archive/next-release/plans/20261113-adrs-and-workflow-off-specs.md)

## Verification

``` bash
uv run pytest scripts/tests
uv run pre-commit run --all-files zizmor
uv run pre-commit run --all-files actionlint
```

## Out of scope

- A change to what the gate or the promotion decides.
- A fix for a defect that a new test finds. `/agentdev:iwe-capture bug` files
  it.

## Key references

- `.github/workflows/ai-responder.yml` — the workflow that holds the four
  decisions of the AI review gate.
- `.github/actions/docker/promote/action.yml` — the action that holds the
  promotion decision.
- `docs/spec-audit/requirements.jsonl` — the rows for `ai-review-gate` and
  `image-pinning` whose `fate` is `needs-test`.
- `AGENTS.md#tests` — the rules that each new test follows.
