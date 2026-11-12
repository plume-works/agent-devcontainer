---
type: plan
created: 2026-11-07
release:
- features/ai-responder-workflows
- bugs/responder-cannot-bypass-iwe-ruleset
description: Remove the free-form `@claude` task responder and every comment, issue, and dispatch trigger of ai-responder.yml, so the workflow runs only on pull request, pull request review, and merge group events.
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/run-claude-responder/action.yml
- resource: zizmor.yaml
- resource: docs/knowledge/data/spec/ai-review-gate.md
- resource: docs/knowledge/data/archive/1.0.0/architecture/dispatched-review-identity.md
- resource: docs/knowledge/data/backlog/drop-claude-free-form-task-trigger.md
stage: done
completed: 2026-11-07
---

# Drop the free-form `@claude` task responder

## Context

Replaces the backlog task [Drop the `@claude <custom prompt>` free-form task
trigger](../backlog/drop-claude-free-form-task-trigger.md) and changes [AI
responder workflows](../../1.0.0/features/ai-responder-workflows.md).

Reviews are requested by toggling the pull request author's assignment, as
[Assignee-triggered AI
re-reviews](../../2.0.0/architecture/assignee-review-trigger.md) records. The
free-form task path is the only remaining user of the comment, issue, and
`workflow_dispatch` triggers, the `bridge` job, the forwarded `requester` input,
and the one job holding `contents: write`.

The maintainer decided on 2026-11-07:

- the free-form task responder is removed;
- the `@claude review` rejection reply is removed with it, so a comment opening
  with `@claude` starts no run at all;
- this plan lands before [The AI responder posts as the plume-works-quill
  App](../../3.0.0/plans/20261030-responder-quill-app-identity.md), which drops
  its task-responder and bridge work.

Removing the task responder ends [Bug: the AI task responder cannot push to iwe/
branches under their ruleset](../bugs/responder-cannot-bypass-iwe-ruleset.md):
no responder job pushes any more.

## Approach

`ai-responder.yml` keeps three triggers: `pull_request` (review, gate,
trusted-bot approval), `pull_request_review` (gate refresh), and `merge_group`.
Every other trigger, the `bridge` and `claude-task` jobs, and every
dispatch-only branch in `preflight` and `ai-review-present` go. Preflight's
write-access check reads `context.actor`, which on a `pull_request` event is the
person who pushed, opened, or assigned.

`run-claude-responder` loses the run-link step and its three inputs, and
`claude-code-action` loses `allowed_bots: github-actions[bot]`, which existed
only so a run dispatched by the bridge's token could act.

With no `issue_comment` trigger, the `dangerous-triggers` ignore for
`.github/workflows/ai-responder.yml#on.pull_request_review` in `zizmor.yaml`
goes too.

A new architecture note records that the responder runs only on pull request
events and supersedes [Dispatched review
identity](../../1.0.0/architecture/dispatched-review-identity.md), which is left
unedited.

Rejected alternatives, recorded in the architecture note:

- **Keep the `@claude review` rejection reply**: it keeps a privileged comment
  trigger and a job on every `@claude` comment, only to redirect a request the
  assignee toggle already covers.
- **Keep the task responder, review-only by default**: the task path is what
  needs `contents: write`, the bridge, and requester forwarding; keeping it
  keeps all three.

## Implementation Steps

### Task 1: The workflow runs only on pull request events

**Files:** Modify: `.github/workflows/ai-responder.yml`

- [x] `on:` lists only `pull_request`, `pull_request_review`, and `merge_group`,
  with their current activity types; the `workflow_dispatch` inputs are gone.
  - **Evidence:** commit 1ddb464f; the Verification grep for `issue_comment` and
    `workflow_dispatch` finds nothing.
- [x] The concurrency group keys runs by pull request number or merge group head
  SHA only.
  - **Evidence:** commit 1ddb464f; `pull_request_review` runs key by pull
    request number and review id, so a review event never cancels a review.
- [x] Preflight's `if:` has no `@claude` clause, its "Determine checkout ref"
  step has no dispatch branch, "Authorize responder requester" reads
  `context.actor`, and "Determine agent prompts" builds only the review prompt,
  with no `wants_task` output.
  - **Evidence:** commit 1ddb464f; the step is renamed "Authorize the triggering
    actor", and `bun build` parses every inline `github-script` body.
- [x] The `bridge` and `claude-task` jobs are removed, `claude-respond` passes
  no run-link inputs, its checkout comment no longer argues the `issue_comment`
  case, and `ai-review-present` reads only `github.event.pull_request.number`.
  - **Evidence:** commit 1ddb464f; the Verification grep finds nothing.

### Task 2: The responder action drops dispatch support

**Files:** Modify: `.github/actions/run-claude-responder/action.yml`,
`zizmor.yaml`

- [x] The `append-run-link`, `comment-id`, and `comment-kind` inputs, the
  "Append run link to Claude request" step, and `allowed_bots` are removed.
  - **Evidence:** commit 1ddb464f; the `pr-number` input, read only by the
    run-link step, is removed too.
- [x] The `dangerous-triggers` ignore entry for
  `.github/workflows/ai-responder.yml#on.pull_request_review` is removed, and
  `actionlint` and `zizmor` pass through pre-commit.
  - **Evidence:** commit 1ddb464f; `uv run pre-commit run --files` on the three
    files passes "Lint GitHub Actions workflow files" and "zizmor".

### Task 3: Catalog and consumer docs drop the task path

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md`,
`.agents/plugins/agentdev/tests/test_request_review.py`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`,
`README.md`

- [x] `pr-request-ai-review` says an `@claude review` comment starts nothing,
  and `test_no_review_trigger_comment_on_any_path`'s docstring no longer
  mentions the bridge;
  `uv run pytest .agents/plugins/agentdev/tests/test_request_review.py` passes.
  - **Evidence:** commit e8c42693; 38 passed.
- [x] The consumption guide's "AI responder and the review gate" section
  describes a workflow that reviews pull requests only: no `@claude` mentions,
  no run-link step, no comment-trigger or `workflow_dispatch` contract, and the
  review refresh is the assignee toggle.
  - **Evidence:** commit e8c42693; the comment-trigger bullet now says no
    comment starts the workflow and forbids adding comment or dispatch triggers.
- [x] `README.md`'s "Pull-request automation" section names reviews only, and
  its security sentence covers the fork gate and the write-access gate on the
  review.
  - **Evidence:** commit e8c42693.
- [x] `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
  - **Evidence:** commit e8c42693; 60/60 skills valid, 0 errors.

### Task 4: Knowledge records the pull-request-only responder

**Files:** Create:
`docs/knowledge/data/archive/2.1.0/architecture/pull-request-only-responder.md`;
Modify: `docs/knowledge/data/architecture.md`,
`docs/knowledge/data/features/ai-responder-workflows.md`

- [x] The architecture note records the decisions under `## Context`, the
  trigger set, both rejected alternatives, and that it supersedes [Dispatched
  review identity](../../1.0.0/architecture/dispatched-review-identity.md); it
  is linked from `data/architecture.md`.
  - **Evidence:** commit 4022927c; `iwe schema validate` passes.
- [x] The feature's `## Purpose`, `## Behaviour`, and `## Edge cases` describe
  no task responder, bridge, or dispatch; the head-branch-without-workflow and
  older-dispatch-input edge cases are removed.
  - **Evidence:** commit 4022927c; the fork edge case now says preflight is
    skipped, matching its `pull_request`-only `if:`.

### Task 5: A comment starts nothing

- [x] After merge, a writer's pull request comment opening with `@claude` starts
  no run of `ai-responder.yml`, and an assignee toggle on the same pull request
  still runs a review whose `ai-review-present` passes.
  - **Evidence:** on #736, comment 6712433638 started no run; the assignment
    started run 42410073078, whose Claude PR Review Responder and
    `ai-review-present` succeeded.

## Spec changes

[AI review gate](../../../spec/ai-review-gate.md):

``` markdown
## MODIFIED Requirements

## Requirement: the responder only acts for authorized same-repository requests

The responder SHALL NOT check out or execute code for a pull request originating
from a fork, and SHALL NOT act for an actor without write access. The PR review
responder SHALL run with read-only repository contents access, and no responder
job SHALL hold write repository contents access.

### Scenario: a fork PR triggers the responder

- **WHEN** the pull request head repository differs from the workflow repository
- **THEN** preflight is skipped, and every responder job is skipped before any
  checkout.

### Scenario: a user without write access triggers the responder

- **WHEN** the actor of a `pull_request` event has a permission other than
  `admin`, `maintain`, or `write`
- **THEN** preflight fails and no responder job runs.

## Requirement: a review runs on first push and on explicit request

The review job SHALL run when a pull request is opened, marked ready for review,
reopened, or assigned, and on a push to a pull request that has no accepted
review. An assignment SHALL run a review whether or not an accepted review
exists. The review job SHALL NOT run for a `pull_request` event on a draft pull
request.

The workflow SHALL be triggered only by pull request, pull request review, and
merge group events: a comment, an issue, or a mention of `@claude` SHALL start
no run, and the workflow SHALL accept no `workflow_dispatch`.

The `ai-review-present` gate SHALL run for pull request, pull request review,
and merge group events.

### Scenario: a draft is opened

- **WHEN** a pull request is opened as a draft
- **THEN** no review runs until the pull request is marked ready for review.

### Scenario: a writer re-requests a review by assignment

- **WHEN** a writer removes a reviewed pull request's author as assignee and
  adds them back
- **THEN** a `pull_request` run reviews the pull request, and its
  `ai-review-present` reports that review.

### Scenario: a writer comments `@claude`

- **WHEN** a writer opens a pull request comment, review comment, or issue with
  `@claude`
- **THEN** no run of the workflow starts.

## Requirement: a pull request can opt out of the AI review run

A pull request whose body carries `[ci:skip-ai-review]` alone on a line SHALL
skip the review responder, whatever event started the run, an assignment
included. The marker SHALL NOT waive the `ai-review-present` gate.

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

## REMOVED Requirements

## Requirement: comment mentions run the pull request branch's workflow

Removed with the free-form task responder: no comment starts a run, so nothing
is bridged to the head branch.
```

[AI review refresh](../../../spec/ai-review-refresh.md) — a rationale comment
starts no workflow run, rather than being one the bridge dispatches nothing for.

[Template consumption](../../../spec/template-consumption.md) — the AI review
gate's trust requirement forbids comment, issue, and `workflow_dispatch`
triggers in place of retaining the `workflow_dispatch` bridge.

## Verification

- `uv run pre-commit run --files .github/workflows/ai-responder.yml .github/actions/run-claude-responder/action.yml zizmor.yaml`
  — `actionlint` and `zizmor` pass.
- `grep -nE "issue_comment|workflow_dispatch|claude-task|bridge|requester|comment_id|allowed_bots|append-run-link" .github/workflows/ai-responder.yml .github/actions/run-claude-responder/action.yml`
  finds nothing.
- `uv run pytest .agents/plugins/agentdev/tests/test_request_review.py` passes.
- `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
- `iwe normalize` and `iwe schema validate` pass.
- Task 5 is observed on GitHub after merge.

## Out of scope

- The review responder, the gate's acceptance rule, and the trusted-bot
  approval, beyond removing dispatch-only inputs.
- The responder's GitHub App identity: [The AI responder posts as the
  plume-works-quill
  App](../../3.0.0/plans/20261030-responder-quill-app-identity.md).
- The cost-analysis scripts `scripts/download-claude-responder-runs.py` and
  `scripts/analyze-claude-responder-costs.py`, which read review runs.

## Key references

- `.github/workflows/ai-responder.yml#on.pull_request_review` — `issue_comment`;
  `.github/workflows/ai-responder.yml#on.pull_request_review.types` —
  `pull_request_review_comment`;
  `.github/workflows/ai-responder.yml#on.pull_request.types` — `issues`;
  `.github/workflows/ai-responder.yml#env` — `workflow_dispatch`
- `.github/workflows/ai-responder.yml#jobs.preflight.steps.Determine checkout ref.id`
  — `concurrency`
- `.github/workflows/ai-responder.yml#jobs.preflight.steps.Authorize the triggering actor.with.script`
  — `wants_task` output
- `.github/workflows/ai-responder.yml#jobs.preflight.steps.name` —
  `DISPATCH_PR_NUMBER`
- `.github/workflows/ai-responder.yml#jobs.claude-respond.permissions` —
  "Authorize responder requester"
- `.github/workflows/ai-responder.yml#jobs.claude-respond.steps.Run Claude responder.with.model`
  — "Determine agent prompts"
- `.github/workflows/ai-responder.yml#jobs.trusted-bot-approval.steps.Approve on behalf of the trusted bot.with.script.per_page`
  — `bridge`
- `.github/workflows/ai-responder.yml#jobs.trusted-bot-approval.steps.Approve on behalf of the trusted bot.with.script`
  — CodeQL TOCTOU checkout comment
- `.github/workflows/ai-responder.yml#jobs.trusted-bot-approval.steps.Approve on behalf of the trusted bot.with.script`
  — `claude-respond` run-link inputs
- `.github/workflows/ai-responder.yml#jobs.trusted-bot-approval.steps.Approve on behalf of the trusted bot.with.script`
  — `claude-task`
- `.github/workflows/ai-responder.yml#jobs.trusted-bot-approval.steps.Approve on behalf of the trusted bot.with.script`
  — `ai-review-present` `pr-number`
- `.github/actions/run-claude-responder/action.yml#inputs.artifact-name` —
  `append-run-link`;
  `.github/actions/run-claude-responder/action.yml#inputs.model.required` —
  `comment-id`; `.github/actions/run-claude-responder/action.yml#runs.using` —
  `comment-kind`;
  `.github/actions/run-claude-responder/action.yml#runs.steps.Run devcontainer lifecycle commands.run`
  — run-link step;
  `.github/actions/run-claude-responder/action.yml#runs.steps.Fail on Claude usage limit.run`
  — `allowed_bots`
- `zizmor.yaml#rules.known-vulnerable-actions.disable` —
  `.github/workflows/ai-responder.yml#on.pull_request_review` ignore
- `.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md#post-the-request › "removed, and the assignees end as the script found them. An"`
  — `@claude review` sentence
- `.agents/plugins/agentdev/tests/test_request_review.py::test_no_review_trigger_comment_on_any_path`
  — bridge docstring
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md#ai-responder-and-the-review-gate`
  — "AI responder and the review gate"
- `README.md#pull-request-automation` — "Pull-request automation"
