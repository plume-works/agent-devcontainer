---
type: plan
created: 2026-10-30
release:
- features/ai-responder-workflows
description: Post every AI responder review, comment, and trusted-bot approval as the plume-works-quill GitHub App, make it the only identity the AI review gate accepts, and retire GitHub Actions' ability to approve pull requests.
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/run-claude-responder/action.yml
- resource: .github/actions/ai-review-status/action.yml
- resource: .github/workflows/renovate.yml
- resource: openspec/specs/ai-review-gate/spec.md
- resource: https://github.com/anthropics/claude-code-action/blob/main/action.yml
- resource: https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/controlling-permissions-for-github_token
- resource: https://docs.github.com/en/code-security/dependabot/troubleshooting-dependabot/troubleshooting-dependabot-on-github-actions
stage: done
completed: 2026-11-07
---

# The AI responder posts as the plume-works-quill App

## Context

Changes [AI responder workflows](../features/ai-responder-workflows.md).

The responder posts with the workflow's `GITHUB_TOKEN`, so its reviews and
comments appear as `github-actions[bot]`, a login every workflow in the
organization shares. Under the one-approval `main` ruleset an approval from that
login satisfies the required review, and [Actions approval
permission](../../../../openspec/specs/ai-review-gate/spec.md#rationale) records
the organization setting this depends on and the reach it grants every workflow.

The maintainer decided on 2026-10-30:

- the responder posts as a GitHub App named `plume-works-quill`, login
  `plume-works-quill[bot]`, for a recognizable reviewer and for an approval no
  other workflow can give;
- the App is the only automated approver: the review responder and the
  trusted-bot approval job both post with its installation token,
  `ai-review-present` accepts only its reviews, and the organization setting
  "Allow GitHub Actions to create and approve pull requests" is turned off once
  the App's approval is shown to count;
- reviews by `github-actions[bot]` and `claude[bot]` are ignored, with no
  transition period and no dismissals;
- the `plume-works-review` environment replaces `claude-review` and holds
  `CLAUDE_CODE_OAUTH_TOKEN`, `QUILL_APP_CLIENT_ID`, and `QUILL_APP_PRIVATE_KEY`;
  a job whose App secrets are missing fails, with no `GITHUB_TOKEN` fallback;
- the App never opens pull requests.

The maintainer decided on 2026-11-07 that `plume-works-quill[bot]` is the only
AI reviewer login, written as a literal wherever a workflow, action, or catalog
skill needs it, with no variable or input to repoint it.

The maintainer decided on 2026-11-07 that the App's installation holds contents
write: the `main` ruleset counts an approval only from a reviewer with write
access, so a read-only App's approval leaves `reviewDecision` at
`REVIEW_REQUIRED`. Every token a job mints stays at contents read or below.

The maintainer decided on 2026-11-07 that [Drop the free-form `@claude` task
responder](20261107-drop-claude-task-responder.md) lands first. With no task
responder, comment bridge, or responder push, this plan covers only the review
responder and the trusted-bot approval, and the App needs no ruleset bypass.

## Approach

```
 environment: plume-works-review
   claude-respond  lifecycle scripts → mint (contents:read)  → claude-code-action
   trusted-bot approval              → mint (pull-requests:write) → APPROVE

 ai-review-present ── accepts plume-works-quill[bot] only
```

`run-claude-responder` mints the installation token with
`actions/create-github-app-token`, after the devcontainer lifecycle scripts and
immediately before the Claude step, naming every permission explicitly the way
`renovate.yml` does. A job's `permissions:` block bounds only `GITHUB_TOKEN`, so
the minted token's `permission-*` inputs are what keep the review responder's
contents access read-only. A preceding step fails the job with a message naming
the missing secret when either App secret is empty.

`claude-code-action` receives the minted token, and `bot_id` and `bot_name`
resolved from the token's `app-slug` (as `renovate.yml` resolves its git
author).

`ai-review-status`, the trusted-bot approval job, `pr-request-ai-review`, and
`pr-eval-review-needed` recognise `plume-works-quill[bot]` as the AI reviewer in
place of `claude[bot]` and `github-actions[bot]`. The workflow runs only on pull
request, pull request review, and merge group events, and the App opens no pull
request and pushes nothing, so no App event can start a review.

The App's installation holds contents read and write, pull requests read and
write, issues read and write, actions read, and metadata read, and no workflows
permission. Contents write is what makes its approval count; no job requests it
when minting, so no workflow token can push, and only a holder of the App's
private key could.

The lifecycle scripts run code from the pull request head in the same job that
later holds the minted token. `GITHUB_TOKEN` carries the same exposure; the fork
and write-access gates bound it to writers, and minting after the scripts keeps
the minted token out of their environment though not out of a process they leave
running.

Rejected alternatives, recorded in the architecture note:

- **Keep `GITHUB_TOKEN` and the organization approval setting**: any workflow in
  the organization can approve as the reviewer and satisfy the required review.
- **The App reviews while `GITHUB_TOKEN` approves trusted bots**: the
  organization setting has to stay on, so the same gap stays open.
- **The Claude GitHub App through OIDC (`claude[bot]`)**: an identity this
  organization does not control, shared with every other installation.
- **Falling back to `GITHUB_TOKEN` when the App secrets are missing**: a silent
  fallback reintroduces the shared identity the gate no longer accepts.

Assumptions:

- The trusted-bot approval job is the one
  [20261030-ai-review-verdicts-and-bot-approval](20261030-ai-review-verdicts-and-bot-approval.md)
  adds; this plan changes only the token it posts with.

## Implementation Steps

### Task 1: The responder action mints and uses the App token

**Files:** Modify: `.github/actions/run-claude-responder/action.yml`

- [x] The action takes the App client ID and the App private key as inputs, and
  fails with a message naming any empty App input before it runs anything else.
  - **Evidence:** commit 56b8be80; inputs `app-client-id` and `app-private-key`,
    and the first step "Require the App secrets" emits an error naming each
    empty secret and fails; pre-commit `zizmor` passes.
- [x] After the lifecycle scripts, it mints an installation token with contents
  read, pull requests write, issues write, and actions read, and resolves the
  App's bot user ID from the token's `app-slug`.
  - **Evidence:** commit 56b8be80; "Create GitHub App token" follows the
    lifecycle step with `permission-contents: read`,
    `permission-pull-requests: write`, `permission-issues: write`,
    `permission-actions: read`, and "Resolve the App's bot user" reads
    `/users/<app-slug>[bot]`; pre-commit `zizmor` passes.
- [x] The Claude step receives the minted token, `bot_id`, and `bot_name`.
  - **Evidence:** commit 56b8be80; the Claude step passes
    `steps.app_token.outputs.token`, `bot_id`, and `bot_name` from "Resolve the
    App's bot user"; pre-commit `zizmor` and `prettier` pass on the action.

### Task 2: The workflow runs the review responder as the App

**Files:** Modify: `.github/workflows/ai-responder.yml`

- [x] `claude-respond` uses `environment: plume-works-review`, passes
  `QUILL_APP_CLIENT_ID` and `QUILL_APP_PRIVATE_KEY` to the action, and drops
  `id-token: write` and its comment.
  - **Evidence:** commit 1c517a54; `claude-respond` names
    `environment: plume-works-review`, passes `secrets.QUILL_APP_CLIENT_ID` and
    `secrets.QUILL_APP_PRIVATE_KEY` as `app-client-id` and `app-private-key`,
    and has no `id-token` permission; actionlint and zizmor pass.
- [x] The workflow has no `AI_REVIEWER_LOGIN`.
  - **Evidence:** commit d8c80b7b removes the workflow `env:` entry and both
    `reviewer-login` inputs; the Verification grep for `AI_REVIEWER_LOGIN` finds
    nothing; actionlint passes.
- [x] The review prompt carries a line saying the responder never opens a pull
  request.
  - **Evidence:** commit 1c517a54; preflight's "Determine agent prompts" adds
    `Never open a pull request.` to the review prompt; actionlint passes.
- [x] `actionlint` and `zizmor` pass through pre-commit.
  - **Evidence:** commit 1c517a54;
    `uv run pre-commit run --files .github/workflows/ai-responder.yml .github/actions/run-claude-responder/action.yml`
    passes "Lint GitHub Actions workflow files" (actionlint) and `zizmor`.

### Task 3: Trusted bots are approved by the App

**Files:** Modify: `.github/workflows/ai-responder.yml`

- [x] The trusted-bot approval job uses `environment: plume-works-review`, fails
  when an App secret is empty, mints a token with only pull requests write, and
  posts its approval with it.
  - **Evidence:** commit 3d9c3828; the job names
    `environment: plume-works-review`, "Require the App secrets" fails naming an
    empty `QUILL_APP_CLIENT_ID` or `QUILL_APP_PRIVATE_KEY`, "Create GitHub App
    token" sets only `permission-pull-requests: write`, and the approval and
    dismissals post through `getOctokit(APP_TOKEN)`; actionlint and zizmor pass.
- [x] Its duplicate-approval check looks for an `APPROVED` review by the literal
  `plume-works-quill[bot]`.
  - **Evidence:** commit d8c80b7b; `ownApprovals` compares `review.user?.login`
    with `'plume-works-quill[bot]'`; every inline script parses under
    `bun build --no-bundle`, and actionlint passes.

### Task 4: The gate accepts only the App's review

**Files:** Modify: `.github/actions/ai-review-status/action.yml`,
`.github/workflows/ai-responder.yml`

- [x] `ai-review-status` accepts a review only from `plume-works-quill[bot]`,
  with no input to change it; its failure message names that login.
  - **Evidence:** commit d8c80b7b; the `reviewer-login` input is gone,
    `reviewerLogin` is the literal `plume-works-quill[bot]`, and the failure
    reason names it; the script parses under `bun build --no-bundle`, and
    actionlint and zizmor pass.
- [x] Neither preflight nor `ai-review-present` passes a reviewer login.
  - **Evidence:** commit d8c80b7b; both `ai-review-status` calls pass only
    `pr-number`, `github-token`, and, for the gate, `trusted-bot-actors`;
    actionlint passes.

### Task 5: Architecture note records the App identity

**Files:** Create: `docs/knowledge/data/architecture/responder-app-identity.md`;
Modify: `docs/knowledge/data/architecture.md`

- [x] The note records the decisions under `## Context`, the token flow and
  permissions under `## Approach`, the residual lifecycle-script exposure, and
  every rejected alternative, and states that it supersedes [Actions approval
  permission](../../../../openspec/specs/ai-review-gate/spec.md#rationale),
  which is left unedited.
  - **Evidence:** commit fe8fa496; `architecture/responder-app-identity` carries
    the decisions under `## Context` including the 2026-11-07 contents write
    decision, the token flow and installation permissions under `## Approach`,
    `## Residual exposure`, all four rejected alternatives, and the line
    superseding `architecture/actions-approval-permission`, which stays
    unchanged; `iwe schema validate` passes.
- [x] The note is linked from `data/architecture.md`.
  - **Evidence:** commit 5b18c551; `data/architecture.md` inclusion-links
    `architecture/responder-app-identity` in key order; `iwe schema validate`
    passes.

### Task 6: Consumer setup describes the App

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`,
`README.md`, `docs/knowledge/data/features/ai-responder-workflows.md`

- [x] The consumption guide's required prerequisites become: register a GitHub
  App with the installation permissions under `## Approach` and install it;
  create the `plume-works-review` environment with `CLAUDE_CODE_OAUTH_TOKEN`,
  `QUILL_APP_CLIENT_ID`, and `QUILL_APP_PRIVATE_KEY` and no deployment branch
  policy. It states that the gate accepts only `plume-works-quill[bot]`. The
  optional Claude GitHub App step is removed.
  - **Evidence:** commit fe8fa496; prerequisite 1 gives the App contents read
    and write, pull requests read and write, issues read and write, actions
    read, metadata read, and no workflows permission, and says why contents
    write is needed; prerequisite 2 is `plume-works-review` with its three
    secrets and no deployment branch policy; the text states only
    `plume-works-quill[bot]` is recognised; `validate_agent_files` reports 0
    errors.
- [x] `README.md` names the App, the `plume-works-review` environment, and the
  three secrets, and no `AI_REVIEWER_LOGIN`.
  - **Evidence:** commit f2c23937; "Pull-request automation" names the
    `plume-works-quill` App, `plume-works-review`, and the three secrets, with
    no `AI_REVIEWER_LOGIN`; prettier passes.
- [x] The feature's `## Behaviour` describes the App identity and the gate's
  single accepted login, `plume-works-quill[bot]`.
  - **Evidence:** commit f2c23937; "The gate accepts one login." names
    `plume-works-quill[bot]` with no variable; `iwe schema validate` passes.
- [x] `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
  - **Evidence:** commit 5e3f5c2f;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    reports 60/60 skills valid, 0 errors.

### Task 10: The catalog and the note name the App's login

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py`,
`.agents/plugins/agentdev/tests/test_request_review.py`,
`.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md`,
`docs/knowledge/data/architecture/responder-app-identity.md`

- [x] `request-review.py` counts a review as the AI's only when its author is
  `plume-works-quill[bot]`, and a test shows a `plume-works-quill[bot]` review
  of the head reports `ALREADY_REVIEWED` while a `github-actions[bot]` one does
  not.
  - **Evidence:** commit 8e197a76; `reviewed()` compares the author with
    `AI_REVIEWER = 'plume-works-quill[bot]'`;
    `uv run pytest .agents/plugins/agentdev/tests/test_request_review.py` passes
    39 tests, including `test_accepted_review_on_head_toggles_nothing` and
    `test_review_by_unaccepted_author_on_head_still_toggles[github-actions[bot]]`.
- [x] `pr-eval-review-needed` names `plume-works-quill` (GraphQL) and
  `plume-works-quill[bot]` (REST) as the AI reviewer.
  - **Evidence:** commit 8e197a76; "Establish what the last review saw" names
    `plume-works-quill` and `plume-works-quill[bot]`; `validate_agent_files`
    reports 0 errors.
- [x] The architecture note names `plume-works-quill[bot]` as the gate's only
  login and no `AI_REVIEWER_LOGIN`.
  - **Evidence:** commit f2c23937; `architecture/responder-app-identity` records
    the 2026-11-07 decision and names the literal login, with no
    `AI_REVIEWER_LOGIN`; `iwe schema validate` passes.

### Task 7: The App and environment exist

- [x] The `plume-works-quill` App is registered with the installation
  permissions under `## Approach` and installed on this repository, and the
  `plume-works-review` environment holds the three secrets.
  - **Evidence:** repository settings, observed 2026-11-07:
    `gh api apps/plume-works-quill` and `gh api orgs/plume-works/installations`
    (installation 179685658, all repositories) both list actions read, contents
    write, issues write, metadata read, and pull requests write;
    `gh api repos/plume-works/agent-devcontainer/environments/plume-works-review/secrets`
    lists `CLAUDE_CODE_OAUTH_TOKEN`, `QUILL_APP_CLIENT_ID`, and
    `QUILL_APP_PRIVATE_KEY`.

### Task 8: The App's review satisfies the ruleset

- [x] After merge, a pull request reviewed by `plume-works-quill[bot]` with
  `APPROVE` reports `reviewDecision: APPROVED` and passes `ai-review-present`.
  - **Evidence:** PR #741, merged as 8516dea7: `plume-works-quill[bot]` approved
    head 5d9e6e2b, `gh pr view 741` reported `reviewDecision: APPROVED` and
    `mergeStateStatus: CLEAN` with `ai-review-present` `SUCCESS` on head
    fa7c3ad0, and `gh pr merge 741 --squash` merged it without `--admin`.

### Task 9: GitHub Actions can no longer approve

- [x] With the organization setting "Allow GitHub Actions to create and approve
  pull requests" turned off, the repository reports
  `can_approve_pull_request_reviews: false`, the next Renovate pull request is
  approved by `plume-works-quill[bot]` and merges without bypass, and the
  `claude-review` environment is deleted.
  - **Evidence:** observed 2026-11-07: with the organization setting off,
    `gh api repos/plume-works/agent-devcontainer/actions/permissions/workflow`
    reports `can_approve_pull_request_reviews: false`; Renovate PR #745 was
    approved by `plume-works-quill[bot]` (`reviewDecision: APPROVED`) and
    auto-merged as 370b9cc6 by `plume-works-renovate`, which is not a `main`
    ruleset bypass actor;
    `gh api repos/plume-works/agent-devcontainer/environments` lists only
    `plume-works-review` and `reformat-commit`.

## Spec changes

[AI review gate](../../../../openspec/specs/ai-review-gate/spec.md):

``` markdown
## MODIFIED Requirements

## Requirement: PRs are blocked until an AI review exists

A pull request SHALL NOT be mergeable until Claude has reviewed it. The
`ai-review-present` check SHALL accept a review only from
`plume-works-quill[bot]`, in state `approved`, `changes_requested`, or `commented`.

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

### Scenario: only another identity has reviewed

- **WHEN** the pull request's only reviews are by `github-actions[bot]` or
  `claude[bot]`
- **THEN** `ai-review-present` treats it as unreviewed.

## ADDED Requirements

## Requirement: the responder acts as its own GitHub App

The review responder and the trusted-bot approval SHALL post with an
installation token of the `plume-works-quill` App, minted per
job with only the permissions that job needs and after any code from the pull
request head has run. A job whose App secrets are missing SHALL fail and SHALL
NOT fall back to `GITHUB_TOKEN`. The App's token SHALL NOT carry contents write
access, and the responder SHALL NOT open a pull request.

### Scenario: the App secrets are missing

- **WHEN** a responder job runs and `QUILL_APP_CLIENT_ID` or
  `QUILL_APP_PRIVATE_KEY` is empty
- **THEN** the job fails naming the missing secret, and nothing is posted.
```

## Depends on

- [AI review verdicts gate merge and trusted bots are
  auto-approved](20261030-ai-review-verdicts-and-bot-approval.md)
- [Drop the free-form `@claude` task
  responder](20261107-drop-claude-task-responder.md)

## Verification

- `uv run pre-commit run --files .github/workflows/ai-responder.yml .github/actions/run-claude-responder/action.yml .github/actions/ai-review-status/action.yml`
  — `actionlint` and `zizmor` pass.
- `grep -nE "id-token|environment: claude-review$|claude\[bot\]" .github/workflows/ai-responder.yml .github/actions/*/action.yml`
  finds nothing.
- `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
- `uv run pytest .agents/plugins/agentdev/tests/test_request_review.py` passes.
- `grep -rn "AI_REVIEWER_LOGIN\|reviewer-login" .github .agents README.md docs/knowledge/data/architecture docs/knowledge/data/features`
  finds nothing.
- `iwe normalize` and `iwe schema validate` pass.
- Tasks 7–9 are observed on GitHub in that order; Task 9 runs only after Task 8
  has passed.

## Out of scope

- Changing which review events the reviewer chooses; the dependency owns it.
- Approving Dependabot pull requests: a run Dependabot triggers cannot read
  environment secrets, so the approval job keeps skipping it.
- Dismissing or migrating reviews by `github-actions[bot]` or `claude[bot]`.
- The `Do not push` rule in the responder prompt.

## Key references

- `.github/actions/run-claude-responder/action.yml#inputs.app-client-id` —
  `app-client-id` input
- `.github/actions/run-claude-responder/action.yml#runs.steps.name` — lifecycle
  scripts step
- `.github/actions/run-claude-responder/action.yml#runs.steps.name` — App token
  mint
- `.github/actions/run-claude-responder/action.yml#runs.steps.name` — Claude
  step
- `.github/workflows/ai-responder.yml#jobs.preflight.steps.name` — preflight
  "Check for an accepted AI review"
- `.github/workflows/ai-responder.yml#jobs.preflight.steps.Determine agent prompts.with.script`
  — prompt rule against opening a pull request
- `.github/workflows/ai-responder.yml#jobs.claude-respond.environment` —
  `claude-respond` environment
- `.github/workflows/ai-responder.yml#jobs.claude-respond.steps.Run Claude responder.with.app-client-id`
  — `claude-respond` App secrets passed to the action
- `.github/workflows/ai-responder.yml#jobs.ai-review-present.steps.name` —
  `ai-review-present` gate step
- `.github/workflows/ai-responder.yml#jobs.trusted-bot-approval` —
  `trusted-bot-approval` job
- `.github/workflows/ai-responder.yml#jobs.trusted-bot-approval.steps.Approve on behalf of the trusted bot.with.script`
  — duplicate-approval check
- `.github/actions/ai-review-status/action.yml#runs.steps.Evaluate AI review acceptance.with.script`
  — accepted reviewer login
- `.github/actions/ai-review-status/action.yml#runs.steps.Evaluate AI review acceptance.with.script`
  — failure message
- `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py::AI_REVIEWER`
  — `AI_REVIEWER`
- `.github/workflows/renovate.yml#jobs.renovate.steps.name` — App token mint
  with explicit permissions
- `.github/workflows/renovate.yml#jobs.renovate.steps.name` — App bot identity
  resolution
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md#ai-responder-and-the-review-gate › "The review responder and the"`
  — responder prerequisites
- `README.md#pull-request-automation › "Reviews and trusted-bot approvals post as the"`
  — adopter prerequisites
