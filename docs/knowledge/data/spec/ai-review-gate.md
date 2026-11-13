---
type: spec
description: How the required AI review gate accepts a review, when the responder is allowed to act on a pull request, which identity and skill review it, and how the review's verdict follows its findings.
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/ai-review-status/action.yml
- resource: .github/actions/run-claude-responder/action.yml
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-review/agent-code/post-review.py
---

# AI review gate

## Requirement: PRs are blocked until an AI review exists

A pull request SHALL NOT be mergeable until Claude has reviewed it. The
`ai-review-present` check SHALL accept a review only from
`plume-works-quill[bot]`, in state `approved`, `changes_requested`, or
`commented`.

The check SHALL NOT require that the review name the pull request's current head
commit. It asserts that the pull request has been reviewed, not that each pushed
commit has been: reviewing every commit is prohibitively expensive, and neither
AI nor human reviewers work that way. Refreshing a review is the author's call,
requested by adding the `request-ai-review` label.

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

## Requirement: the responder acts as its own GitHub App

The review responder and the trusted-bot approval SHALL post with an
installation token of the `plume-works-quill` App, minted per job with only the
permissions that job needs and after any code from the pull request head has
run. A job whose App secrets are missing SHALL fail and SHALL NOT fall back to
`GITHUB_TOKEN`. The App's token SHALL NOT carry contents write access, and the
responder SHALL NOT open a pull request.

Both jobs SHALL run in the `plume-works-review` environment, which holds
`CLAUDE_CODE_OAUTH_TOKEN`, `QUILL_APP_CLIENT_ID`, and `QUILL_APP_PRIVATE_KEY`.
The review job SHALL mint its token with contents read, pull requests write,
issues write, and actions read, and SHALL hand `claude-code-action` that token
with the `bot_id` and `bot_name` resolved from the token's App slug. The
trusted-bot approval SHALL read reviews, commits, and branch activity with
`GITHUB_TOKEN`, holding contents read and pull requests read, and SHALL mint its
App token with pull requests write alone, to post or dismiss its approval.
`plume-works-quill[bot]` SHALL be written as a literal wherever the reviewer
login is matched, with no variable or input that repoints it.

### Scenario: the App secrets are missing

- **WHEN** a responder job runs and `QUILL_APP_CLIENT_ID` or
  `QUILL_APP_PRIVATE_KEY` is empty
- **THEN** the job fails naming the missing secret, and nothing is posted.

### Scenario: Claude posts a review

- **WHEN** the review job runs Claude on a pull request
- **THEN** the review and its inline comments appear as
  `plume-works-quill[bot]`, posted with a token minted after the devcontainer
  lifecycle scripts ran.

## Requirement: the responder only acts for authorized same-repository requests

The responder SHALL NOT check out or execute code for a pull request originating
from a fork, and SHALL NOT act for an actor without write access. The PR review
responder SHALL run with read-only repository contents access, and no responder
job SHALL hold write repository contents access.

Preflight SHALL authorize the actor of the `pull_request` event itself: no run
SHALL forward a requester identity to another, and the responder SHALL NOT pass
`claude-code-action` an `allowed_bots` list.

### Scenario: a fork PR triggers the responder

- **WHEN** the pull request head repository differs from the workflow repository
- **THEN** preflight is skipped, every responder job is skipped before any
  checkout, and `ai-review-present` still runs and fails unless an accepted
  review exists.

### Scenario: a user without write access triggers the responder

- **WHEN** the actor of a `pull_request` event has a permission other than
  `admin`, `maintain`, or `write`
- **THEN** preflight fails and no responder job runs.

## Requirement: the review job reviews with the pr-review skill as a submitted review

The review job SHALL run in the `agentdev-devcontainer` image and SHALL prompt
Claude to review with the fully qualified `agentdev:pr-review` skill, naming the
built-in `code-review` skill as one not to use. `run-claude-responder` SHALL NOT
set `claude-code-action`'s `track_progress` input, so the review's findings
reach the pull request as a submitted pull request review. When the pinned image
has no `agentdev-runtime` on `PATH`, `run-claude-responder` SHALL install it
from the checkout's `py_packages/agentdev_runtime/` with `uv tool install`
before running the lifecycle commands, so the review job keeps working while the
image pin trails the package.

### Scenario: the review job reviews a pull request

- **WHEN** the review job runs on a pull request
- **THEN** Claude reviews it with `agentdev:pr-review`, and its findings appear
  as a pull request review with inline comments, not as an issue comment.

### Scenario: the pinned image predates the runtime CLI

- **WHEN** the review job's image has no `agentdev-runtime` command
- **THEN** `run-claude-responder` installs it from a copy of the checkout's
  package, outside the reviewed checkout, and then runs
  `agentdev-runtime lifecycle created` and `lifecycle ready --no-wait`.

## Requirement: the review never executes code

The PR review responder SHALL NOT run tests, builds, linters, dependency
installs or syncs, `docker`, or `devcontainer` commands, in its own session or
in any subagent it dispatches; CI runs them. The `pr-review` skill SHALL state
this, and the review job SHALL deny those commands and nested shells through
`--disallowedTools`.

Only the main review session SHALL read CI results, once, while composing the
review, and only to cite a check that has already finished. No part of the
review SHALL wait for CI: the review job SHALL deny `sleep`, `gh run watch`,
`gh pr checks --watch`, and the `Monitor` tool.

### Scenario: a review pass tries to confirm a finding by running tests

- **WHEN** a review pass or validator runs `uv run pytest`, alone, chained after
  another command, or inside `bash -c`
- **THEN** the command is denied and the finding rests on the code alone.

### Scenario: CI is still running when the review is composed

- **WHEN** the main review session reads `gh pr checks` and the check behind a
  finding has not finished
- **THEN** the review posts the finding without citing that check, and does not
  wait for it.

## Requirement: a review runs on first push and on explicit request

The review job SHALL run when a pull request is opened, marked ready for review,
or reopened, on a push to a pull request that has no accepted review, and when
the `request-ai-review` label is added. The label SHALL run a review whether or
not an accepted review exists. Every run in the pull request's concurrency group
SHALL take a `request-ai-review` it finds on the pull request: the run SHALL
review when the request is authorized and the pull request is not a draft, and
while the pull request carries no `block-ai-reviews`, and the review job SHALL
remove the label with the reviewer App's token once the review finishes, whether
it succeeded or failed, and SHALL NOT remove it when the review is cancelled. A
request whose own run was cancelled while pending is therefore taken by the run
that replaced it. A run that does not review SHALL leave the label for a later
run in that group, as SHALL a run started by another label. A cancelled review
therefore leaves the label until the next run in that group takes it, or until
`request-review.py` re-sends it. An assignment, a reviewer request, and a
reviewer request's removal SHALL NOT start a run. The review job SHALL NOT run
for a `pull_request` event on a draft pull request.

Every other label event, adding or removing any other label, SHALL NOT run a
review and SHALL NOT share the pull request's concurrency group, so it never
replaces a queued review run. Preflight does not run on a fork or bot-authored
pull request, so a `request-ai-review` label added there is not removed.

The workflow SHALL be triggered only by pull request, pull request review, and
merge group events: a comment, an issue, or a mention of `@claude` SHALL start
no run, and the workflow SHALL accept no `workflow_dispatch`.

The `ai-review-present` gate SHALL run for every pull request, pull request
review, and merge group event, every label event included.

### Scenario: a writer requests a review with the label

- **WHEN** a writer adds `request-ai-review` to a reviewed pull request
- **THEN** a `pull_request` run reviews the pull request, its review job then
  removes the label as `plume-works-quill`, and its `ai-review-present` reports
  that review.

### Scenario: a push replaces a pending request

- **WHEN** `request-ai-review` is added while another run of the pull request is
  in progress, and a push queues before the request's run starts
- **THEN** the push's run reviews the pull request, its review job removing the
  label.

### Scenario: a push lands during a requested review

- **WHEN** a push cancels a review that `request-ai-review` started
- **THEN** the label stays, and the push's run reviews the new head and removes
  it.

### Scenario: a user without write access adds the label

- **WHEN** a user with triage but not write access adds `request-ai-review`
- **THEN** preflight fails, no review runs, and the label stays until a run a
  writer starts reviews the pull request.

### Scenario: an unrelated label is added

- **WHEN** a label other than `request-ai-review` is added while a requested
  review is queued
- **THEN** no review runs for the label, the queued review keeps its place, and
  `ai-review-present` in the label's run reports on the existing reviews.

## Requirement: a pull request can block every AI review

While a pull request carries the `block-ai-reviews` label, no review SHALL run
for it, whatever event starts the run, an explicit `request-ai-review` included.
A `request-ai-review` added while the block is on SHALL stay on the pull
request, and removing `block-ai-reviews` SHALL start a run in the pull request's
concurrency group, which takes the waiting `request-ai-review` and reviews it.
The label SHALL NOT waive the `ai-review-present` gate.

Preflight SHALL read the pull request's labels when it runs, not from the event
payload. A label added after a run's preflight read them does not apply to that
run.

The gate SHALL NOT read the label, because a job skipped by its own `if:`
satisfies a required status check, and a label the gate honoured would let
anyone who can label a pull request self-waive the mandatory review. A blocked
pull request with no accepted review keeps a red gate, and only a user with
ruleset bypass can merge it.

### Scenario: a blocked pull request triggers the workflow

- **WHEN** a pull request carrying `block-ai-reviews` is opened or pushed to and
  no accepted review exists
- **THEN** no review responder runs, and `ai-review-present` runs and fails.

### Scenario: a blocked pull request already has an accepted review

- **WHEN** a pull request carrying `block-ai-reviews` has an accepted review and
  receives a push
- **THEN** no review responder runs, and `ai-review-present` passes on the
  existing review.

## Requirement: the AI review verdict follows its findings

The review responder SHALL submit `APPROVE` when no validated finding remains or
every validated finding is non-blocking, and SHALL submit `REQUEST_CHANGES` when
any blocking finding remains, whether or not it is attached inline. It SHALL NOT
choose `COMMENT`, except as the retry when GitHub rejects a verdict because the
reviewer owns the pull request.

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

### Scenario: the title or description is stale

- **WHEN** the pull request's title or description materially misdescribes its
  diff
- **THEN** the review stops before the in-depth passes and submits
  `REQUEST_CHANGES` with the metadata finding in its body.

## Requirement: trusted-bot pull requests are approved without an AI review

The AI responder workflow SHALL approve a same-repository pull request whose
author is a `Bot` listed in `TRUSTED_BOT_ACTORS`, with a review body stating
that the AI review was skipped, only when every commit on the pull request is
authored by that bot, committed by that bot or `web-flow`, and carries a
verified signature, and only when that bot made the head branch's latest
creation and every push and force push since. When any commit or update fails
that check it SHALL NOT approve, SHALL dismiss its own standing approval, and
SHALL post a notice naming the failing push or commit. It SHALL NOT check out
the pull request, SHALL NOT approve a pull request that already carries its
approval, and SHALL skip a run triggered by `dependabot[bot]`, which cannot read
the App secrets in the `plume-works-review` environment.

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

- **WHEN** an account other than the author bot pushes a commit that leaves the
  workflow unchanged to a trusted-bot pull request the workflow already approved
- **THEN** the workflow dismisses its approval, approves nothing, and the pull
  request needs a human approval to merge, even after it is closed and reopened.

### Scenario: a reused branch name starts clean

- **WHEN** a trusted bot recreates a branch whose earlier life included a
  person's push, and opens a new pull request from it
- **THEN** only the pushes since the branch's latest creation are checked, and
  the workflow approves the new pull request.

### Scenario: a person's run on a Dependabot pull request

- **WHEN** a writer's event starts a run on a pull request whose every commit
  and push is `dependabot[bot]`'s own
- **THEN** the workflow approves it, while a run `dependabot[bot]` itself
  triggered approves nothing.

## Rationale

### The AI review verdict follows severity alone

The verdict is `APPROVE` for no or only non-blocking findings and
`REQUEST_CHANGES` for any blocking finding. The `main` ruleset requires one
approving review, keeps stale reviews on push, and requires every review thread
to be resolved; only the reviewer's own `APPROVE` satisfies the approval and
lifts its earlier change request, and inline threads on an approving review
still hold the merge.

Rejected:

- **`COMMENT` when every blocking finding is anchored inline.** A `COMMENT`
  neither satisfies the required approval nor lifts the reviewer's earlier
  change request.
- **`APPROVE` beside anchored blocking findings, relying on thread resolution.**
  An approval next to an unaddressed blocking finding reads as sign-off on it.
- **`COMMENT` for every finding, never `REQUEST_CHANGES`.** A blocking finding
  never blocks through the verdict, and no review satisfies the required
  approval.

### Trusted-bot approval checks the branch's whole push history

The approval covers only the bot's own commits and the bot's own pushes since
the branch's latest creation, and a failed check dismisses the standing
approval, because the `main` ruleset keeps stale approvals on push. The job runs
the pull request's own copy of the workflow, so a writer who edits the job can
bypass it; the checks guard against commits that leave the workflow unchanged,
and the approval is only as strong as the trust in the repository's writers.

Rejected:

- **Check only the actor of a `synchronize` run.** A person's push followed by
  closing and reopening the pull request would restore the approval.
- **Skip Dependabot pull requests by author.** The commit and push checks
  already keep a person's change out of the approval, so an author skip would
  only withhold approval from pull requests holding Dependabot's commits alone.
- **A `pull_request_target` approval workflow.** It would also approve from
  Dependabot-triggered runs, but adds a dangerous-trigger workflow for a bot
  this repository does not configure for version updates.
- **Ruleset bypass for the Renovate App.** It removes the approval requirement
  for dependency bumps instead of recording an approval on each.

### The responder posts as its own GitHub App

`plume-works-quill` is the only automated approver: an identity this
organization controls, whose approval no other workflow can give. The App's
installation holds contents write because the `main` ruleset counts an approval
only from a reviewer with write access; no job mints a token with it, so no
workflow token can push. The lifecycle scripts run pull request code in the job
that later holds the minted token; minting after them keeps the token out of
their environment, and the fork and write-access gates bound that exposure to
writers.

Rejected:

- **Post with `GITHUB_TOKEN` and enable the organization setting that lets
  Actions approve pull requests.** Any workflow in the organization could then
  approve as the reviewer and satisfy the required review.
- **The App reviews while `GITHUB_TOKEN` approves trusted bots.** The
  organization setting has to stay on, so the same gap stays open.
- **The Claude GitHub App through OIDC (`claude[bot]`).** An identity this
  organization does not control, shared with every other installation.
- **Fall back to `GITHUB_TOKEN` when the App secrets are missing.** A silent
  fallback reintroduces the shared identity the gate no longer accepts.
- **A responder job that pushes with `GITHUB_TOKEN` as a ruleset bypass actor.**
  A ruleset bypass list accepts only repository roles, teams, and GitHub Apps
  installed on the repository's owner; the built-in GitHub Actions app behind
  `GITHUB_TOKEN` is none of these, so such a push can never bypass.

### The responder runs only on pull request events

Every run executes the pull request's own copy of the workflow, so no run is
privileged by a default-branch trigger, no identity is forwarded between runs,
and no job needs contents write.

Rejected:

- **A free-form `@claude <prompt>` task responder.** It needs contents write, a
  bridge that dispatches onto the head branch, and requester forwarding.
- **A comment-requested review dispatched onto the head branch.** A
  `workflow_dispatch` run's checks are not counted by the `main` ruleset or the
  status rollup, its actor is `github-actions[bot]` rather than the requester,
  and it needs `allowed_bots` opened on `claude-code-action`.
- **A reply rejecting `@claude review` comments.** It keeps a privileged comment
  trigger and a job on every `@claude` comment only to redirect a request the
  label already covers.

### Reviews are requested with a label and held with a label

`request-ai-review` is the one way to request a review, and `block-ai-reviews`
holds every review while it is on. A label event is a `pull_request` event, so
its run's checks land on the head commit and count toward merge.

Rejected:

- **Assigning the pull request.** It borrows a field that means ownership, and a
  re-request takes two actions, removing then re-adding the assignee.
- **Re-requesting a reviewer.** It needs a second collaborator, since an author
  cannot request their own review, and leaves reviewer churn on the pull
  request.
- **A comment trigger.** A comment-started run is not a `pull_request` run, so
  its gate does not count toward merge, and it needs free-form comment parsing.
- **A state label kept until the review posts.** A failed review leaves the
  label on, to be removed by hand before the next request.
- **A skip label that an explicit request overrides.** A label named for
  skipping reviews that still lets a request through reads as broken.
- **A repository-wide review pause.** A per-PR `block-ai-reviews` covers a
  Claude outage, and a pause would still need bypass merges unless it waived the
  gate.
- **A gate waiver honoured when `getCollaboratorPermissionLevel` shows the
  labeller can write.** It keeps the waiver and only narrows who holds it, so a
  writer could merge unreviewed work with no trace in the branch-protection
  record; ruleset bypass expresses the same intent through a permission GitHub
  already audits.

### The review is a submitted review from the repository's own skill

The required gate counts only a submitted review, and only the agentdev
`pr-review` skill publishes its findings as one.

Rejected:

- **An unqualified "pr-review skill" in the prompt.** It also matches Claude
  Code's built-in `code-review` skill, whose findings are never posted in a
  headless run.
- **Setting `track_progress` for the custom prompt.** It restores tag-mode
  tracking comments and routes the findings into a regular pull request comment
  instead of a submitted review.

### The review reads code and never runs it

CI already runs every test, build, and lint suite in jobs of its own, so a
review that runs them repeats CI's work on the review's clock and adds no
finding the code and CI's logs do not already show. The skill states the rule so
every harness follows it; the deny list enforces it in Claude Code, where it
binds subagents too. Nested shells are denied with the rest because a deny rule
cannot see a command inside `bash -c`.

Rejected:

- **The skill rule alone.** A pass that decides a test run would confirm its
  finding runs one; nothing stops it.
- **The deny list alone.** It binds only the Claude Code review job, while the
  skill also runs under other harnesses and locally.
- **Letting a validator run tests to confirm a finding.** CI reports the same
  failure, and a finding with a complete Trigger, Path, and Outcome stands
  without it.
- **Letting passes and validators read CI, or anyone wait for it.** CI's suites
  run alongside the review and often finish after it, so a pass that consults CI
  waits on it; one look from the main session at composition costs nothing.

### The gate is a job of the review workflow

`ai-review-present` depends on the review job through `needs:`, so the head
commit carries a pending check for as long as a review runs, and the gate reads
the pull request from its own run's event.

Rejected:

- **A separate gate workflow started by `workflow_run`.** It leaves the head
  commit with no pending signal while a review runs, so auto-merge can fire
  mid-review, and it has to rediscover the pull request number across runs.
