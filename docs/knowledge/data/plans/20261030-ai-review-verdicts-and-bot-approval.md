---
type: plan
created: 2026-10-30
release:
- features/ai-responder-workflows
- bugs/ai-rereview-comment-keeps-changes-requested
description: Make the AI reviewer approve unless a blocking finding survives, request changes on any blocking finding, and have the AI responder workflow approve pull requests from trusted bots, so the one-approval main ruleset is satisfiable without bypass.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T19:30:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/ai-review-status/action.yml
- resource: docs/knowledge/data/architecture/ai-review-event-selection.md
- resource: docs/knowledge/data/architecture/actions-approval-permission.md
- resource: docs/knowledge/data/spec/ai-review-gate.md
- resource: docs/knowledge/data/spec/template-consumption.md
---

# AI review verdicts gate merge and trusted bots are auto-approved

## Context

Fixes [Bug: an AI re-review that comments leaves its own change request blocking
merge](../bugs/ai-rereview-comment-keeps-changes-requested.md), and changes [AI
responder workflows](../features/ai-responder-workflows.md).

The `main` ruleset requires one approving review, with thread resolution
required, stale reviews kept on push, and no last-push approval. An `APPROVE`
from `github-actions[bot]` satisfies that approval, which [Actions approval
permission](../architecture/actions-approval-permission.md) records along with
the organization setting it depends on. A pending `CHANGES_REQUESTED` blocks
merge until the same reviewer approves or the review is dismissed.

Two consequences followed for the setup this plan changes:

- `pr-review` Step 9 submitted `COMMENT` whenever its blocking findings were all
  anchored inline or only non-blocking findings remained. A `COMMENT` never
  satisfies the required approval and never replaces the reviewer's own change
  request, so such a pull request needed a clean re-review or ruleset bypass to
  merge.
- Bot-authored pull requests got no AI review, and `ai-review-present` waived
  its requirement for the trusted bots, but nothing approved them. Renovate's
  automerged pull requests stayed `BLOCKED` on `REVIEW_REQUIRED`.

The maintainer decided on 2026-10-30:

- the reviewer submits `APPROVE` when it has no validated findings or only
  non-blocking ones, the thread-resolution rule still gating merge on any inline
  comment; blocking findings always block, so any blocking finding, inline or
  not, submits `REQUEST_CHANGES`;
- the AI responder workflow approves pull requests authored by every login in
  the trusted-bot list, posting an approval whose body states that the AI review
  was skipped and that it approves for the bot; one list governs both the gate
  waiver and the approval;
- the approval runs as a job in `ai-responder.yml` on the `pull_request` event;
  a `pull_request` run triggered by Dependabot holds a read-only `GITHUB_TOKEN`,
  so `dependabot[bot]` stays in the trusted list, and the approval job skips,
  with a notice, a run that `dependabot[bot]` triggers;
- the approval holds only while the pull request carries nothing but the bot's
  own commits, so no one can push a change past review under a bot's approval;
  the same check lets a person-triggered run approve a Dependabot pull request,
  whose commits are Dependabot's alone.

## Approach

The review event becomes a function of finding severity alone:

| Validated findings          | Event             |
| --------------------------- | ----------------- |
| none                        | `APPROVE`         |
| non-blocking only           | `APPROVE`         |
| any blocking, inline or not | `REQUEST_CHANGES` |

`COMMENT` stops being a chosen event. It remains the retry when GitHub rejects a
verdict because the reviewer owns the pull request, which now covers `APPROVE`
as well as `REQUEST_CHANGES`. A clean re-review always submits `APPROVE`, which
replaces the reviewer's own earlier change request — that is the bug's fix.

Inline comments on an approving review still open threads, and
`required_review_thread_resolution` holds the merge until each is resolved, so
approving with non-blocking findings loses no enforcement.

Trusted-bot approval is a new job in `ai-responder.yml` that needs no checkout
and no preflight. It runs on `pull_request` events whose author is a `Bot` on a
same-repository head, matches the author exactly against the trusted list, skips
when the triggering actor is `dependabot[bot]`, and skips when
`github-actions[bot]` already has an `APPROVED` review on the pull request, so a
push does not stack approvals.

Before approving, the job checks every commit on the pull request: its GitHub
author is the pull request's author, its committer is that author or `web-flow`
(GitHub's committer for commits an App creates through the API), and its
signature verifies. A `synchronize` run also requires the triggering actor to be
the pull request's author, because a commit created through the API by another
account can name the bot as author and still verify. When any check fails, the
job approves nothing, dismisses a standing `github-actions[bot]` approval, and
posts a notice naming the failing commit; the ruleset keeps stale approvals on
push, so a standing approval would otherwise cover the new commit. The trusted
list moves to a workflow-level `TRUSTED_BOT_ACTORS` variable that both this job
and `ai-review-present` read.

Rejected alternatives, recorded in the architecture note:

- **`COMMENT` for anchored blocking findings** (the superseded rule): it neither
  satisfies the required approval nor replaces an earlier change request.
- **`APPROVE` with anchored blocking findings, relying on thread resolution**:
  the maintainer ruled that blocking findings always block; an approval shown
  beside an unaddressed blocking finding reads as sign-off on it.
- **A `pull_request_target` workflow for trusted-bot approval**: it would also
  approve Dependabot, but adds a dangerous-trigger workflow for a bot this
  repository does not configure for version updates.
- **Ruleset bypass for the Renovate App**: it removes the approval requirement
  for dependency bumps instead of recording an approval on each.
- **Skipping Dependabot pull requests by author**: the commit check already
  keeps a person's change out of a bot approval, so the author skip would only
  withhold approval from pull requests that hold Dependabot's commits alone.

Assumptions:

- The Codex single-call tool takes `APPROVE` or `COMMENT` only; a Codex review
  that must submit `REQUEST_CHANGES` uses the bundled `post-review.sh` instead.

- The approval body is:

  ``` text
  AI review skipped: this pull request is authored by <login>, a trusted bot. Approving on its behalf.
  ```

## Implementation Steps

### Task 1: Review event follows finding severity

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

- [x] Step 9 selects `APPROVE` for no validated findings or only non-blocking
  findings, and `REQUEST_CHANGES` for any blocking finding, inline or not; the
  `COMMENT` branch is removed.
  - **Evidence:** commit `de50d28` — `pr-review/SKILL.md` Step 9 lists only the
    `APPROVE` and `REQUEST_CHANGES` rules.
- [x] The self-owned retry covers both verdicts: when GitHub rejects `APPROVE`
  or `REQUEST_CHANGES` because the account owns the pull request, retry as
  `COMMENT` and say so in the body.
  - **Evidence:** commit `de50d28` — Step 9 retries a rejected `APPROVE` or
    `REQUEST_CHANGES` as `COMMENT` and notes it in the body.
- [x] The severity-tier definitions, the Codex single-call option, and the
  fallback-script contract state the same rule; the Codex option routes
  `REQUEST_CHANGES` through `post-review.sh`.
  - **Evidence:** commit `de50d28` — the severity tiers, the Codex single-call
    option, and the fallback `--event` contract state the rule; Codex routes
    `REQUEST_CHANGES` through `post-review.sh`.
- [x] The `validate-agent-files` pre-commit hook passes on the changed skill.
  - **Evidence:** commit `de50d28` —
    `uv run pre-commit run --files .agents/plugins/agentdev/skills/pr-review/SKILL.md`
    passed `validate-agent-files` and `prettier`.

### Task 2: Trusted-bot pull requests are approved

**Files:** Modify: `.github/workflows/ai-responder.yml`

- [x] A workflow-level `TRUSTED_BOT_ACTORS` env holds
  `renovate[bot],plume-works-renovate[bot],dependabot[bot]`, and
  `ai-review-present` passes it to `ai-review-status` instead of the inline
  literal.
  - **Evidence:** commit `06d3beb` — `ai-responder.yml:81` defines the env;
    `ai-review-present` passes `${{ env.TRUSTED_BOT_ACTORS }}` at
    `ai-responder.yml:533`.
- [x] A new job approves a `pull_request` (`opened`, `reopened`, `synchronize`,
  `ready_for_review`) whose author is a `Bot` listed exactly in
  `TRUSTED_BOT_ACTORS`, on a same-repository head, under the existing
  `repository_owner` gate, with `pull-requests: write` only and no checkout.
  - **Evidence:** commit `06d3beb` — job `trusted-bot-approval`
    (`ai-responder.yml:562`) gates on owner, the four actions, same-repository
    head, and `user.type == 'Bot'`, matches the login exactly against
    `TRUSTED_BOT_ACTORS`, with `pull-requests: write` only and no checkout.
- [x] The job skips with a notice when `github.actor` is `dependabot[bot]`, and
  skips when `github-actions[bot]` already has an `APPROVED` review on the pull
  request.
  - **Evidence:** commit `06d3beb` — the script posts a notice and returns when
    `context.actor` is `dependabot[bot]`, and returns when a
    `github-actions[bot]` `APPROVED` review exists.
- [x] The approval body is the text under `## Approach`, with `<login>` replaced
  by the author's login.
  - **Evidence:** commit `06d3beb` — `createReview` body is the `## Approach`
    text with the author's login interpolated.
- [x] `actionlint` and `zizmor` pass through pre-commit.
  - **Evidence:** commit `06d3beb` —
    `uv run pre-commit run --files .github/workflows/ai-responder.yml` passed
    actionlint and zizmor.

### Task 3: Architecture note records the new event rule

**Files:** Modify:
`docs/knowledge/data/architecture/ai-review-event-selection.md`

- [x] `## Decision` states the severity-only rule from `## Approach`; the
  `COMMENT`-preference rationale is replaced by the one-approval ruleset and the
  per-reviewer change-request rule it must satisfy.
  - **Evidence:** commit `390c699` — `## Decision` carries the severity table;
    `## Why the verdict follows severity` rests it on the one-approval ruleset
    and the per-reviewer change-request rule; `iwe schema validate` passed.
- [x] The superseded rule and the anchored-blocking `APPROVE` variant are listed
  under `## Alternatives rejected` with the reasons in `## Approach`.
  - **Evidence:** commit `390c699` — `## Alternatives rejected` lists `COMMENT`
    for anchored blocking findings and `APPROVE` with anchored blocking
    findings, with the `## Approach` reasons.

### Task 4: Feature and template guidance describe the approval

**Files:** Modify: `docs/knowledge/data/features/ai-responder-workflows.md`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [x] The feature's `## Behaviour` describes the verdict rule and the
  trusted-bot approval, including the Dependabot skip.
  - **Evidence:** commit `c600879` — `ai-responder-workflows.md` `## Behaviour`
    adds the verdict rule and the trusted-bot approval with the Dependabot skip;
    `iwe schema validate` passed.
- [x] The consumption guide's trusted-bot bullets say the same list drives the
  approval, and that a consumer's ruleset needs the organization's Actions
  approval setting for either verdict path.
  - **Evidence:** commit `c600879` — the consumption guide's bot-gate and
    `TRUSTED_BOT_ACTORS` bullets name the approval, and a new bullet requires
    the organization's Actions approval setting for both verdict paths;
    `validate_agent_files` passed.

### Task 5: Trusted-bot approval requires the bot's own commits

**Files:** Modify: `.github/workflows/ai-responder.yml`,
`docs/knowledge/data/architecture/ai-review-event-selection.md`,
`docs/knowledge/data/features/ai-responder-workflows.md`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [x] `trusted-bot-approval` lists the pull request's commits and approves only
  when each one's GitHub author is the pull request's author, its committer is
  that author or `web-flow`, and `verification.verified` is true, and, on
  `synchronize`, when `github.actor` is the pull request's author.
  - **Evidence:** commit `9a6226c` — the job's script fails on a `synchronize`
    push whose `context.actor` is not the author, else lists commits and
    requires author login, committer login or `web-flow`, and
    `verification.verified`.
- [x] When the check fails, the job approves nothing, dismisses any `APPROVED`
  review from `github-actions[bot]` on the pull request, and posts a notice
  naming the first failing commit and the reason.
  - **Evidence:** commit `9a6226c` — on failure the script dismisses every
    `github-actions[bot]` `APPROVED` review and posts a notice naming the
    failing commit SHA or pushed head and the reason.
- [x] The architecture note records the commit check and the rejected author
  skip; the feature's `## Behaviour` and the consumption guide replace
  "Dependabot pull requests stay unapproved" with the commit check and the
  approval a person-triggered run gives a Dependabot pull request.
  - **Evidence:** commit `c8c5676` — `ai-review-event-selection.md` adds
    `## Trusted-bot approval covers only the bot's commits` and rejects the
    Dependabot author skip; the feature doc and consumption guide describe the
    commit check and the person-triggered Dependabot approval.
- [x] `actionlint` and `zizmor` pass through pre-commit, and
  `iwe schema validate` passes.
  - **Evidence:** commits `9a6226c` and `c8c5676` —
    `uv run pre-commit run --files .github/workflows/ai-responder.yml` passed
    actionlint and zizmor; `iwe schema validate` passed in the `c8c5676`
    pre-commit run.

### Task 6: A trusted-bot pull request merges without bypass

- [ ] After the change is on `main`, the next Renovate pull request receives the
  bot approval and merges through Renovate's automerge with no ruleset bypass,
  or the plan records that the ruleset's
  `require_extra_approval_for_unattributed_changes` demanded another approval.

### Task 7: A review with only non-blocking findings approves

- [ ] A pull request reviewed after the change, whose validated findings are all
  non-blocking, carries an `APPROVED` review from `github-actions[bot]`, and
  merges once its threads are resolved.

## Spec changes

[AI review gate](../spec/ai-review-gate.md):

``` markdown
## ADDED Requirements

## Requirement: the AI review verdict follows its findings

The review responder SHALL submit `APPROVE` when no validated finding remains
or every validated finding is non-blocking, and SHALL submit `REQUEST_CHANGES`
when any blocking finding remains, whether or not it is attached inline. It
SHALL NOT choose `COMMENT`, except as the retry when GitHub rejects a verdict
because the reviewer owns the pull request.

### Scenario: a re-review finds only non-blocking issues

- **WHEN** the AI reviewer earlier requested changes on a pull request and a
  re-review finds only non-blocking issues
- **THEN** the re-review is an `APPROVE` with inline comments, the reviewer's
  change request no longer blocks merge, and merge waits only for the inline
  threads to be resolved.

### Scenario: a review finds an anchored blocking issue

- **WHEN** a review finds a blocking issue and attaches it inline
- **THEN** the review is `REQUEST_CHANGES`, and the pull request stays blocked
  until a later review from the same reviewer approves it.

## Requirement: trusted-bot pull requests are approved without an AI review

The AI responder workflow SHALL approve a same-repository pull request whose
author is a `Bot` listed in `TRUSTED_BOT_ACTORS`, with a review body stating
that the AI review was skipped, only when every commit on the pull request is
authored by that bot, committed by that bot or `web-flow`, and carries a
verified signature, and, for a push, only when that bot pushed. When any commit
fails that check it SHALL NOT approve, and SHALL dismiss its own standing
approval. It SHALL NOT check out the pull request, SHALL NOT approve a pull
request that already carries its approval, and SHALL skip a run triggered by
`dependabot[bot]`, whose token cannot approve.

### Scenario: Renovate opens a pull request

- **WHEN** `plume-works-renovate[bot]` opens a pull request on a branch of this
  repository
- **THEN** the workflow approves it once, no AI review runs, and
  `ai-review-present` passes on the trusted-bot waiver.

### Scenario: a bot outside the list opens a pull request

- **WHEN** a bot not listed in `TRUSTED_BOT_ACTORS` opens a pull request
- **THEN** no approval and no AI review is posted, and the pull request stays
  blocked unless merged by ruleset bypass.

### Scenario: a person pushes to a trusted-bot pull request

- **WHEN** an account other than the author bot pushes a commit to a
  trusted-bot pull request the workflow already approved
- **THEN** the workflow dismisses its approval, approves nothing, and the pull
  request needs a human approval to merge.
```

[Template consumption](../spec/template-consumption.md):

``` markdown
## MODIFIED Requirements

## Requirement: the AI review gate's trust is explicit

The `claude-respond` and `ai-review-present` jobs in `ai-responder.yml` SHALL be
kept or dropped together. The responder SHALL NOT auto-review any bot-authored
pull request; `ai-review-present` SHALL waive its requirement, and the
trusted-bot approval job SHALL approve, only for the bot logins listed in
`TRUSTED_BOT_ACTORS`, matched exactly and only when `user.type` is `Bot`. The
gate checks that the pull request has a review, not that its head commit does —
a copy comparing the review's `commit_id` to the head SHA is a policy change.
The fork gate and write-access gate SHALL be preserved as written; the owner
gate SHALL be repointed at the consumer. The `workflow_dispatch` bridge SHALL be
retained so default-branch comment events can run the pull request head
branch's workflow and attach checks to that head.
```

## Verification

- `uv run pre-commit run --files .github/workflows/ai-responder.yml` —
  `actionlint` and `zizmor` pass.
- `uv run pre-commit run --files .agents/plugins/agentdev/skills/pr-review/SKILL.md`
  — the agent-file validation hook passes.
- `grep -n "COMMENT" .agents/plugins/agentdev/skills/pr-review/SKILL.md` shows
  `COMMENT` only as the self-owned retry and in the Codex tool's accepted
  actions.
- `iwe normalize` and `iwe schema validate` pass.
- Tasks 6 and 7 are observed on live pull requests after merge; the maintainer
  accepted that live observation, with no automated test of the approval job, as
  the coverage for the spec scenarios.

## Out of scope

- Moving the reviewer to a GitHub App identity (`plume-works-quill[bot]`); a
  later plan owns it.
- Approving a Dependabot pull request from a Dependabot-triggered run.
- Dismissing change requests already standing on open pull requests.
- Changing what `ai-review-present` accepts as a review.

## Key references

Verified anchor points (line numbers as of 2026-10-30):

- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:27` — Codex single-call
  `action` values
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:79` — severity tier
  definitions
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:125` — Step 3 metadata
  gate
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:149` — Step 9 event
  selection
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:153` — self-owned
  `APPROVE`/`REQUEST_CHANGES` retry
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:190` — fallback script
  `--event`
- `.github/workflows/ai-responder.yml:77` — workflow `env`
- `.github/workflows/ai-responder.yml:98` — preflight owner gate and bot skip
- `.github/workflows/ai-responder.yml:504` — `ai-review-present` job
- `.github/workflows/ai-responder.yml:533` — `trusted-bot-actors` read from
  `TRUSTED_BOT_ACTORS`
- `.github/workflows/ai-responder.yml:562` — `trusted-bot-approval` job
- `.github/workflows/ai-responder.yml:589` — Dependabot actor skip
- `.github/workflows/ai-responder.yml:625` — commit check
- `.github/workflows/ai-responder.yml:654` — `createReview` approval
- `.github/actions/ai-review-status/action.yml:60` — trusted-bot waiver
- `docs/knowledge/data/architecture/ai-review-event-selection.md:16` —
  `## Decision`
- `docs/knowledge/data/architecture/ai-review-event-selection.md:73` —
  `## Trusted-bot approval covers only the bot's commits`
- `docs/knowledge/data/architecture/ai-review-event-selection.md:92` —
  `## Alternatives rejected`
- `docs/knowledge/data/spec/template-consumption.md:99` — "the AI review gate's
  trust is explicit"
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:413`
  — trusted-bot guidance
