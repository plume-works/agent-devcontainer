---
type: plan
created: 2026-10-30
release:
- features/ai-responder-workflows
description: Post every AI responder review, comment, and trusted-bot approval as the plume-works-quill GitHub App, make it the only identity the AI review gate accepts, and retire GitHub Actions' ability to approve pull requests.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-07T12:00:00Z
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/run-claude-responder/action.yml
- resource: .github/actions/ai-review-status/action.yml
- resource: .github/workflows/renovate.yml
- resource: docs/knowledge/data/architecture/actions-approval-permission.md
- resource: docs/knowledge/data/architecture/dispatched-review-identity.md
- resource: https://github.com/anthropics/claude-code-action/blob/main/action.yml
- resource: https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/controlling-permissions-for-github_token
- resource: https://docs.github.com/en/code-security/dependabot/troubleshooting-dependabot/troubleshooting-dependabot-on-github-actions
rank: 1000
---

# The AI responder posts as the plume-works-quill App

## Context

Changes [AI responder workflows](../features/ai-responder-workflows.md).

The responder posts with the workflow's `GITHUB_TOKEN`, so its reviews and
comments appear as `github-actions[bot]`, a login every workflow in the
organization shares. Under the one-approval `main` ruleset an approval from that
login satisfies the required review, and [Actions approval
permission](../architecture/actions-approval-permission.md) records the
organization setting this depends on and the reach it grants every workflow.

The maintainer decided on 2026-10-30:

- the responder posts as a GitHub App named `plume-works-quill`, login
  `plume-works-quill[bot]`, for a recognizable reviewer and for an approval no
  other workflow can give;
- the App is the only automated approver: the review responder and the
  trusted-bot approval job both post with its installation token,
  `ai-review-present` accepts only its reviews, and the organization setting
  "Allow GitHub Actions to create and approve pull requests" is turned off once
  the App's approval is shown to count;
- reviews by the previous bot identities are ignored, with no transition period
  and no dismissals;
- the `plume-works-review` environment replaces `claude-review` and holds
  `CLAUDE_CODE_OAUTH_TOKEN`, `QUILL_APP_CLIENT_ID`, and `QUILL_APP_PRIVATE_KEY`;
  a job whose App secrets are missing fails, with no `GITHUB_TOKEN` fallback;
- the App never opens pull requests.

The maintainer decided on 2026-11-07 that [Drop the free-form `@claude` task
responder](20261107-drop-claude-task-responder.md) lands first. With no task
responder, comment bridge, or responder push, this plan covers only the review
responder and the trusted-bot approval, and the App needs no contents write
access and no ruleset bypass.

## Approach

```
 environment: plume-works-review
   claude-respond  lifecycle scripts → mint (contents:read)  → claude-code-action
   trusted-bot approval              → mint (pull-requests:write) → APPROVE

 ai-review-present ── accepts AI_REVIEWER_LOGIN only
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

The accepted reviewer login moves to a workflow-level `AI_REVIEWER_LOGIN`
variable, set to `plume-works-quill[bot]`, which `ai-review-status` reads in
place of its hard-coded set. The workflow runs only on pull request, pull
request review, and merge group events, and the App opens no pull request and
pushes nothing, so no App event can start a review.

The App's installation holds contents read, pull requests read and write, issues
read and write, actions read, and metadata read; no contents write and no
workflows permission, so the App can push nothing.

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

- `AI_REVIEWER_LOGIN` is a workflow `env` value, so a consumer repoints it in
  one place; the template keeps `plume-works-quill[bot]`.
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
- [x] A workflow-level `AI_REVIEWER_LOGIN` is `plume-works-quill[bot]`.
  - **Evidence:** commit 1c517a54; the workflow `env:` sets
    `AI_REVIEWER_LOGIN: 'plume-works-quill[bot]'`; actionlint passes.
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
- [x] Its duplicate-approval check looks for an `APPROVED` review by
  `AI_REVIEWER_LOGIN` instead of `github-actions[bot]`.
  - **Evidence:** commit 3d9c3828; `ownApprovals` filters `APPROVED` reviews by
    `process.env.AI_REVIEWER_LOGIN`; every inline script parses under
    `bun build --no-bundle`, and actionlint passes.

### Task 4: The gate accepts only the App's review

**Files:** Modify: `.github/actions/ai-review-status/action.yml`,
`.github/workflows/ai-responder.yml`

- [ ] `ai-review-status` takes the accepted reviewer login as an input and
  accepts a review only from that login; its failure message names it.
- [ ] `ai-review-present` passes `AI_REVIEWER_LOGIN`.

### Task 5: Architecture note records the App identity

**Files:** Create: `docs/knowledge/data/architecture/responder-app-identity.md`;
Modify: `docs/knowledge/data/architecture.md`

- [ ] The note records the decisions under `## Context`, the token flow and
  permissions under `## Approach`, the residual lifecycle-script exposure, and
  every rejected alternative, and states that it supersedes [Actions approval
  permission](../architecture/actions-approval-permission.md), which is left
  unedited.
- [ ] The note is linked from `data/architecture.md`.

### Task 6: Consumer setup describes the App

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`,
`README.md`, `docs/knowledge/data/features/ai-responder-workflows.md`

- [ ] The consumption guide's required prerequisites become: register a GitHub
  App with the installation permissions under `## Approach` and install it;
  create the `plume-works-review` environment with `CLAUDE_CODE_OAUTH_TOKEN`,
  `QUILL_APP_CLIENT_ID`, and `QUILL_APP_PRIVATE_KEY` and no deployment branch
  policy; set `AI_REVIEWER_LOGIN` to the App's bot login. The optional Claude
  GitHub App step is removed.
- [ ] `README.md` names the App, the environment, and the three secrets where it
  now names `claude-review` and one secret.
- [ ] The feature's `## Behaviour` describes the App identity and the gate's
  single accepted login.
- [ ] `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes.

### Task 7: The App and environment exist

- [ ] The `plume-works-quill` App is registered with the installation
  permissions under `## Approach` and installed on this repository, and the
  `plume-works-review` environment holds the three secrets.

### Task 8: The App's review satisfies the ruleset

- [ ] After merge, a pull request reviewed by `plume-works-quill[bot]` with
  `APPROVE` reports `reviewDecision: APPROVED` and passes `ai-review-present`.

### Task 9: GitHub Actions can no longer approve

- [ ] With the organization setting "Allow GitHub Actions to create and approve
  pull requests" turned off, the repository reports
  `can_approve_pull_request_reviews: false`, the next Renovate pull request is
  approved by `plume-works-quill[bot]` and merges without bypass, and the
  `claude-review` environment is deleted.

## Spec changes

[AI review gate](../spec/ai-review-gate.md):

``` markdown
## MODIFIED Requirements

## Requirement: PRs are blocked until an AI review exists

A pull request SHALL NOT be mergeable until Claude has reviewed it. The
`ai-review-present` check SHALL accept a review only from the login named by
`AI_REVIEWER_LOGIN`, which this repository sets to `plume-works-quill[bot]`, in
state `approved`, `changes_requested`, or `commented`.

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
installation token of the App whose bot login is `AI_REVIEWER_LOGIN`, minted per
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
- `grep -n "id-token\|claude-review\|claude\[bot\]" .github/workflows/ai-responder.yml .github/actions/*/action.yml`
  finds nothing.
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes.
- `iwe normalize` and `iwe schema validate` pass.
- Tasks 7–9 are observed on GitHub in that order; Task 9 runs only after Task 8
  has passed.

## Out of scope

- Changing which review events the reviewer chooses; the dependency owns it.
- Approving Dependabot pull requests: a run Dependabot triggers cannot read
  environment secrets, so the approval job keeps skipping it.
- Dismissing or migrating reviews by the previous bot identities.
- The `Do not push` rule in the responder prompt.

## Key references

Verified anchor points (line numbers as of 2026-11-07):

- `.github/actions/run-claude-responder/action.yml:11` — `github_token` input
- `.github/actions/run-claude-responder/action.yml:28` — lifecycle scripts step
- `.github/actions/run-claude-responder/action.yml:88` — Claude step
- `.github/workflows/ai-responder.yml:103` — preflight "Check for an accepted AI
  review"
- `.github/workflows/ai-responder.yml:111` — "Authorize the triggering actor"
- `.github/workflows/ai-responder.yml:186` — prompt security rules
- `.github/workflows/ai-responder.yml:207` — `claude-respond` `id-token: write`
- `.github/workflows/ai-responder.yml:209` — `claude-respond` environment
- `.github/workflows/ai-responder.yml:224` — `claude-respond` secrets passed to
  the action
- `.github/workflows/ai-responder.yml:284` — `trusted-bot-approval` job
- `.github/actions/ai-review-status/action.yml:68` — `claudeLogins`
- `.github/actions/ai-review-status/action.yml:97` — failure message
- `.github/workflows/renovate.yml:75` — App token mint with explicit permissions
- `.github/workflows/renovate.yml:90` — App bot identity resolution
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:361`
  — responder prerequisites
- `README.md:351` — adopter prerequisites
