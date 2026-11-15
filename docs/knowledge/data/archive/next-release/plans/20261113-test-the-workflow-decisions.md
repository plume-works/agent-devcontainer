---
type: plan
created: 2026-11-13
release: internal
stage: done
completed: 2026-11-15
description: Move the decision logic of the AI review gate and of the image promotion out of the workflow files into scripts, and add a test that runs each decision.
sources:
- resource: docs/spec-audit/requirements.jsonl
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/docker/promote/action.yml
---

# Test the decisions that the workflows make

## Context

[The spec usefulness audit](../../../findings/spec-usefulness-audit.md) found
five behaviours that only a spec states and that are inline code in a workflow
file. Four are in `spec/ai-review-gate` and one is in `spec/image-pinning`. Each
one decides a merge or a publish, and nothing runs it before GitHub does.

The test rules in `AGENTS.md#tests` permit only a test that runs the behaviour.
A test cannot run code that is a string in a YAML file.

This plan is a part of [Shrink the knowledge base to an issue tracker and
decision records](../../../backlog/shrink-knowledge-base-to-issues-and-adrs.md).
It is a separate plan because a mistake in it shows only on a real pull request
or a real publish.

## Approach

The decisions of the AI review gate move to the JavaScript module
`.github/actions/ai-review-status/review-gate.js`. Each `actions/github-script`
step keeps its calls to GitHub, loads the module with `require`, and calls one
function. A `bun test` runs each function with inputs that the test controls.
The decision of the image promotion moves to a shell script that the action
calls. A test runs the script with inputs that the test controls.

The move changes no behaviour. Two observation tasks confirm that on GitHub.

## Implementation Steps

### Task 1: Move and test the decisions of the AI review gate

**Files:** Create: `.github/actions/ai-review-status/review-gate.js`,
`.github/actions/ai-review-status/review-gate.test.js`; Modify:
`.github/workflows/ai-responder.yml`,
`.github/actions/ai-review-status/action.yml`, `.github/workflows/ci.yml`

Each test shows what the `fate_note` of its row in
`docs/spec-audit/requirements.jsonl` says.

- [x] A test runs "PRs are blocked until an AI review exists".
  - **Evidence:** `.github/actions/ai-review-status/review-gate.test.js` runs
    `reviewAcceptance` of `.github/actions/ai-review-status/review-gate.js`;
    `bun test ./.github/actions/ai-review-status` passes 42 tests.
- [x] A test runs "the responder only acts for authorized same-repository
  requests".
  - **Evidence:** the same test file runs `isFork` and `canTrigger` for each
    head repository and permission level.
- [x] A test runs "a review runs on first push and on explicit request".
  - **Evidence:** the same test file runs `wantsReview` for each pull request
    action, label event, draft, and label state.
- [x] A test runs "trusted-bot pull requests are approved without an AI review".
  - **Evidence:** the same test file runs `isTrustedBot` and
    `botApprovalFailure` for foreign commits, foreign pushes, and a reused
    branch.
- [x] `.github/workflows/ai-responder.yml` calls the module for each of the four
  decisions and holds no copy of them in a step. The `concurrency:` group and
  the `if:` of each job stay, because GitHub reads them before a step runs.
  - **Evidence:** The `github-script` steps of the `preflight` job, the
    `trusted-bot-approval` job, and
    `.github/actions/ai-review-status/action.yml` call the module. The two jobs
    check out `.github/actions/ai-review-status` for the module. Zizmor and
    actionlint pass.

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

- [x] The gate blocks the pull request before the AI review exists.
  - **Evidence:** on pull request #890, the first one after this change that
    needs an AI review, the required check `ai-review-present` of run
    43663125415 stayed pending from 01:26 until the AI review job ended at 01:30
    UTC.
- [x] The gate passes after the AI review is submitted.
  - **Evidence:** after the review of `plume-works-quill[bot]` at 01:30:05 UTC,
    `reviewAcceptance` from the module logged "Found accepted AI review" and
    `ai-review-present` passed in run 43663125415.

### Task 4: Observe an image promotion

**Closed by:** the first image build on the default branch after this change.

- [x] The promotion step publishes the tag of the tested image.
  - **Evidence:** in run 43654311837 on `main` at `19156ec6`, the job
    `Promote development image` called `tag-decision.sh` for each tag, and moved
    `edge` and `main` of the four images to the tested digests.

## Acceptance

None — no behavioral change

## Depends on

[Add ADRs and take the workflow off
specs](20261113-adrs-and-workflow-off-specs.md)

## Verification

``` bash
uv run pytest scripts/tests
bun test ./.github/actions/ai-review-status
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

## Ship review

`iwe-ship-reviewer` did this review on 2026-11-15.

- [x] Verify found no CRITICAL problem — correct: Ready to ship:
  data/plans/20261113-test-the-workflow-decisions
- [x] Every ADR that the plan proposed is `stage: accepted` — not applicable:
  the plan proposed no ADR
- [x] Every ADR that the plan superseded is `stage: superseded` and in the
  archive — not applicable: the plan superseded no ADR
- [x] The plan is `stage: done` with `completed` and no `rank` — correct:
  2026-11-15
- [x] Every feature in `release` is `stage: implemented` — not applicable:
  `release` lists no feature
- [x] Every bug in `release` is `stage: done` with no `rank` — not applicable:
  `release` lists no bug
- [x] Every bug in `release` has a `## Fix` that links this plan — not
  applicable: `release` lists no bug
- [x] The plan and every feature and bug that it completed are in the archive,
  and no hub links them — correct:
  data/archive/next-release/plans/20261113-test-the-workflow-decisions
