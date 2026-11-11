---
type: plan
created: 2026-09-09
release:
- features/ai-responder-workflows
description: Resume an interrupted Claude pull-request review from a persistent local session when a writer adds the resume-ai-review label.
sources:
- resource: https://github.com/plume-works/agent-devcontainer/actions/runs/34403145254/job/102639842076?pr=134
  title: Interrupted PR 134 review
- resource: https://github.com/plume-works/agent-devcontainer/actions/runs/34414950294
  title: Failed review with attached execution output
- resource: https://github.com/anthropics/claude-code-action/blob/v1/action.yml
  title: Claude Code Action outputs
- resource: https://github.com/anthropics/claude-code-action/blob/v1/base-action/src/run-claude-sdk.ts
  title: Claude Code Action SDK execution
- resource: https://github.com/github/docs/blob/main/data/reusables/actions/jobs/section-running-jobs-in-a-container-volumes.md
  title: GitHub Actions job-container volumes
- resource: docs/knowledge/data/architecture/assignee-review-trigger.md
- resource: docs/knowledge/data/plans/20261030-responder-quill-app-identity.md
- resource: docs/knowledge/data/architecture/label-review-triggers.md
- resource: docs/knowledge/data/plans/20261108-label-review-triggers.md
stage: cancelled
---

# Resume interrupted Claude PR reviews on a persistent runner

## Cancellation

Cancelled: the review runner's Claude subscription now has enough 5-hour usage
that a review no longer runs out of quota mid-run, so interrupted reviews are
not a recurring failure worth a persistent-session resume path.

## Context

The [AI responder workflow](../features/ai-responder-workflows.md) runs each
Claude review in a disposable job container. A long review can therefore reach a
usage limit after substantial work, while the next job has neither the local
Claude transcript nor a supported way to continue it.

The responder uploads its execution file when one is available after execution.
Resumption also requires the corresponding persistent transcript tree and
session identifier.

Reviews are requested with pull request labels ([Label-triggered AI
reviews](../architecture/label-review-triggers.md), shipped by [Request and
block AI reviews with labels](20261108-label-review-triggers.md)): adding
`request-ai-review` fires a `pull_request`/`labeled` run whose
`ai-review-present` counts toward merge, and `block-ai-reviews` holds every
review. A resume request follows the same model: it is a third label, handled by
the same routing, block, and label-removal rules.

The review job posts as the `plume-works-quill` App ([The AI responder posts as
the plume-works-quill App](20261030-responder-quill-app-identity.md)), in the
`plume-works-review` environment, with an installation token minted inside
`run-claude-responder` after the devcontainer lifecycle scripts. A resume run
inherits that identity and token flow unchanged.

The maintainer decided on 2026-11-08:

- the resume label is `resume-ai-review`, named like `request-ai-review`;
- while `block-ai-reviews` is on, a `resume-ai-review` waits like a request: no
  resume runs, the label stays on, and removing `block-ai-reviews` runs it;
- when a pull request carries both `request-ai-review` and `resume-ai-review`,
  the resume wins: the run resumes the stored session, or refuses it, and takes
  both labels;
- a refused resume does not fail the review job: the job posts one diagnostic
  comment, removes the label, and ends successfully without invoking Claude, so
  `ai-review-present` reports the pull request's real review state.

## Approach

Run only the `claude-respond` job on one persistent self-hosted runner carrying
the custom label `claude-review`. Mount a runner-local named Docker volume,
`agentdev-claude-review-sessions`, at `/github/home/.claude/projects` inside
every review job container. This keeps Claude's transcripts and subagent
transcript tree across disposable containers without persisting its credentials,
settings, or plugin registry. Non-agent jobs remain on their current hosted
runners.

Each initialized review attempt records an atomic, repository-and-PR-scoped
`latest` metadata document in that volume containing its run ID, head SHA,
session ID, conclusion, and transcript location. A resume request selects that
latest prior attempt automatically. Before Claude starts, it refuses missing,
malformed, completed, transcript-less, or head-mismatched state, and refuses
when an accepted AI review already exists; a refusal posts one operational PR
comment naming the reason and ends the job successfully without Claude. A valid
attempt passes the stored session ID to Claude with `--resume` and a
continuation prompt saying that review passes whose results the transcript does
not hold were lost with the prior process and must be run again.

`resume-ai-review` joins the routing `request-ai-review` already has: adding it
puts the run in the pull request's `pr-<n>` concurrency group, preflight reads
it from the live label list, `block-ai-reviews` holds it, and any run in that
group takes it. The review job removes it, and any `request-ai-review` with it,
with the App token once the resume finishes or is refused, and never when the
job is cancelled. A push that cancels a resume leaves the label for the push's
run, which then refuses the stale head. A fresh review, requested with
`request-ai-review` alone, never selects stored session state. Automatic waiting
and scheduled retries are out of scope.

Rejected alternatives: a `@claude review resume` comment, because a dispatched
run's gate does not count toward merge; a body marker, because a marker stays in
the body and turns every later review into a resume attempt; failing the job on
a refusal, because a failed review job turns `ai-review-present` red on a pull
request that may already be reviewed; uploading and restoring the whole Claude
home as an artifact, which duplicates state already on the persistent runner,
increases secret exposure, and adds artifact download orchestration; and
persisting only the execution output, which is not the transcript format
`--resume` consumes.

Registering the runner host with the `claude-review` label and its
operating-system maintenance remain external administration. The
`plume-works-review` GitHub environment and the App secrets it holds are
prerequisites the self-hosted runner receives for each review job as a hosted
runner does. The persistent volume holds only `.claude/projects`, so neither the
App private key nor a minted token outlives the job container. The repository
declares the required runner label and Docker volume; the implementation is not
complete until a CI run proves that external prerequisite.

The workflow keeps one latest-attempt metadata pointer per repository and pull
request and never deletes Claude-owned transcript files. Claude's configured
transcript retention and the runner administrator own garbage collection and
volume capacity; the resume workflow only reads and writes its namespaced
metadata.

## Implementation Steps

### Task 1: Give review containers a persistent Claude transcript store

**Files:** Modify: `.github/workflows/ai-responder.yml`

- [ ] Route `claude-respond` to `[self-hosted, claude-review]`, leaving
  preflight, trusted-bot approval, and gate runner selection unchanged.
- [ ] Mount the named Docker volume `agentdev-claude-review-sessions` at
  `/github/home/.claude/projects` in the review job container, keeping the
  remainder of Claude's home disposable.

### Task 2: Record and resolve resumable review attempts

**Files:** Create: `.github/actions/run-claude-responder/session_state.py`,
`.github/actions/run-claude-responder/test_session_state.py`; Modify:
`.github/actions/run-claude-responder/action.yml`,
`.github/workflows/validate-agent-files.yml`

- [ ] Add a standard-library-only helper that atomically records the latest
  initialized review attempt per repository and PR from the execution file,
  using validated numeric run/PR identifiers and a UUID session identifier.
- [ ] Make the helper resolve the latest prior attempt and distinguish valid
  state from each refusal reason: no record, malformed metadata, current or
  completed run, head-SHA mismatch, invalid session ID, and missing or ambiguous
  transcript.
- [ ] Invoke recording under `always()` whenever the Claude action produced an
  execution file, including provider-limit failures, without weakening the
  existing execution-artifact upload or failure result.
- [ ] Cover recording, atomic replacement, repository/PR isolation, successful
  resolution, and every refusal reason with focused pytest tests; run that test
  file in `validate-agent-files.yml` when `.github/**` changes.

### Task 3: Route the resume label like a request

**Files:** Modify: `.github/workflows/ai-responder.yml`

- [ ] Adding `resume-ai-review` joins the `pr-<n>` concurrency group and runs
  preflight, beside adding `request-ai-review` and removing `block-ai-reviews`;
  every other label event keeps its own `label-<run id>` group.
- [ ] Preflight reads `resume-ai-review` from the live label list and outputs a
  resume flag; `wantsReview` treats it as a request, after the block check and
  under the same draft, fork, bot-author, and writer-authorization checks, with
  the label's adder as the requester of a `labeled` run.
- [ ] `claude-respond` receives the resume flag, and the label-removal input
  names both labels when the resume flag is set.

### Task 4: Resume or refuse before Claude starts

**Files:** Modify: `.github/actions/run-claude-responder/action.yml`

- [ ] Before invoking Claude for a resume, resolve the previous attempt and also
  refuse when an accepted AI review already exists. On any refusal, post exactly
  one top-level operational comment, as the App with the job's minted token,
  naming the reason and current run, remove `resume-ai-review` and any
  `request-ai-review`, and end the job successfully without invoking Claude.
  This comment is workflow diagnostics, not a review finding.
- [ ] For valid state, pass the resolved session ID through the responder's
  `claude_args` as `--resume` and replace the fresh-review request with a
  continuation instruction that says review passes whose results the transcript
  lacks were lost with the prior process and must be run again, and that
  completed work must not be duplicated.
- [ ] After a resumed Claude step finishes with success or failure, remove
  `resume-ai-review` and any `request-ai-review` with the App token, under the
  same `!cancelled()` success-or-failure condition as the "Take the review
  request label" step; a cancelled job removes neither.
- [ ] Keep the current fork, writer-authorization, immutable-head checkout,
  content-permission, and `ai-review-present` gates in force for resume runs.

### Task 5: Make the review skill safe after process loss

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

- [ ] Define resumed-run handling: reuse pass results already returned in the
  transcript, and run again only the initial or validation passes whose results
  the transcript lacks.
- [ ] Define idempotent review publication: if interruption left an unsubmitted
  pending review, discard and reconstruct it from the validated findings before
  one final submission; if an accepted review already exists, publish nothing
  further.

### Task 6: Record the runner boundary and consumer adaptation

**Files:** Create:
`docs/knowledge/data/architecture/resumable-ai-review-sessions.md`; Modify:
`docs/knowledge/data/architecture.md`,
`docs/knowledge/data/features/ai-responder-workflows.md`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [ ] Record the session-state boundary, dedicated-runner decision, label
  routing, block and both-label rules, refusal outcome, volume contents,
  metadata key, validation order, retention ownership, and rejected comment,
  body-marker, failing-refusal, artifact, and full-home alternatives in the
  architecture graph.
- [ ] Update the feature description to include explicit, validated review
  continuation by `resume-ai-review` without weakening the existing review gate.
- [ ] Add the dedicated `claude-review` self-hosted runner, its Docker daemon,
  and the `resume-ai-review` label as required external prerequisites in the
  template-consumption guide, beside the `request-ai-review` and
  `block-ai-reviews` labels, and tell consumers that keep the responder workflow
  to adapt the runner label and persistence policy to their infrastructure.

### Task 7: Prove continuation on the dedicated runner

**Files:** External configuration and GitHub Actions evidence only

- [ ] Register exactly one persistent runner with the `self-hosted` and
  `claude-review` labels and a Docker daemon that retains the named volume
  between jobs.
  - **Closed by:** the maintainer.
- [ ] Produce an interrupted review attempt that records a session, then add
  `resume-ai-review` after capacity is available; verify the next job selects
  the prior run automatically, uses the same session ID and head SHA, continues
  the review, submits no duplicate review, removes the label, and satisfies
  `ai-review-present`.
  - **Closed by:** the maintainer, on a pull request running this workflow.
- [ ] Add `resume-ai-review` on a pull request with no recorded attempt; verify
  the run skips Claude, succeeds, posts exactly one reason-bearing comment, and
  removes the label.
  - **Closed by:** the maintainer, on a pull request running this workflow.
- [ ] Add `resume-ai-review` after the head changed since the recorded attempt;
  verify the run skips Claude, succeeds, posts exactly one reason-bearing
  comment, and removes the label.
  - **Closed by:** the maintainer, on a pull request running this workflow.

## Spec changes

[AI review gate](../spec/ai-review-gate.md):

``` markdown
## ADDED Requirements

## Requirement: interrupted Claude reviews resume only from valid persistent state

A writer adding the `resume-ai-review` label to a pull request SHALL start a
`pull_request` `labeled` run in the pull request's concurrency group, whose
`ai-review-present` counts toward merge. Every run in that group SHALL take a
`resume-ai-review` it finds, under the same authorization, draft, and
`block-ai-reviews` rules as `request-ai-review`; when both labels are on the
pull request, the run SHALL resume and SHALL take both.

The responder SHALL select the latest prior Claude review attempt recorded for
that repository and pull request and SHALL invoke Claude with `--resume` only
when the attempt is incomplete, its session transcript exists unambiguously, no
accepted AI review already exists, and its recorded head SHA equals the current
pull-request head. Otherwise the review job SHALL NOT invoke Claude, SHALL post
exactly one pull-request comment naming the refusal and the run, SHALL remove
the labels, and SHALL succeed, so `ai-review-present` reports the existing
reviews. The review job SHALL remove the labels with the reviewer App's token
once a resumed review finishes, whether it succeeded or failed, and SHALL NOT
remove them when the job is cancelled.

Every Claude review attempt that initializes a session and produces execution
output SHALL atomically record its run ID, pull-request number, head SHA,
session ID, conclusion, and transcript location in persistent runner-local
state before the job exits. A resume run SHALL preserve all existing fork,
requester-authorization, immutable-checkout, permission, and review-gate
controls.

### Scenario: an interrupted review is resumed

- **WHEN** a writer adds `resume-ai-review`, the latest prior review attempt is
  incomplete, its transcript is available, its head SHA is current, and no
  accepted AI review exists
- **THEN** the workflow resumes that session, reuses completed pass results,
  runs again the passes whose results were lost, submits at most one
  pull-request review, and removes the label.

### Scenario: no prior review attempt exists

- **WHEN** a writer adds `resume-ai-review` and no prior review attempt is
  recorded for that pull request
- **THEN** Claude is not invoked, the review job succeeds, the label is removed,
  and the workflow posts exactly one pull-request comment naming the missing
  prior attempt and the run.

### Scenario: the pull-request head changed

- **WHEN** the selected prior attempt's recorded head SHA differs from the
  current pull-request head
- **THEN** Claude is not invoked, the review job succeeds, the label is removed,
  and the workflow posts exactly one pull-request comment naming the stale-head
  refusal and the run.

### Scenario: prior session state is unusable

- **WHEN** the selected attempt is completed, its metadata or session ID is
  invalid, or its transcript is missing or ambiguous
- **THEN** Claude is not invoked, the review job succeeds, the label is removed,
  and the workflow posts exactly one pull-request comment naming the refusal and
  the run.

### Scenario: a review already exists

- **WHEN** the pull request already has an accepted AI review when a resume is
  requested
- **THEN** Claude is not invoked, the review job succeeds, the label is removed,
  the workflow posts exactly one pull-request comment stating that there is no
  incomplete review to resume, and `ai-review-present` passes on the existing
  review.

### Scenario: both labels are on the pull request

- **WHEN** a run finds both `request-ai-review` and `resume-ai-review`
- **THEN** it resumes the stored session, or refuses it, and removes both labels.

### Scenario: a writer requests a fresh review

- **WHEN** a writer adds `request-ai-review` to a pull request without
  `resume-ai-review`
- **THEN** the workflow starts a fresh review session and does not select or
  resume stored session state.

## MODIFIED Requirements

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

Removing `block-ai-reviews` SHALL start a run in the pull request's concurrency
group, which takes a waiting `request-ai-review` or `resume-ai-review`. Adding
`resume-ai-review` SHALL start a run in that group, as "interrupted Claude
reviews resume only from valid persistent state" requires. Every other label
event, adding or removing any other label, SHALL NOT run a review and SHALL NOT share
the pull request's concurrency group, so it never replaces a queued review run.
Preflight does not run on a fork or bot-authored pull request, so a
`request-ai-review` label added there is not removed.

The workflow SHALL be triggered only by pull request, pull request review, and
merge group events: a comment, an issue, or a mention of `@claude` SHALL start
no run, and the workflow SHALL accept no `workflow_dispatch`.

The `ai-review-present` gate SHALL run for every pull request, pull request
review, and merge group event, every label event included.

### Scenario: a draft is opened

- **WHEN** a pull request is opened as a draft
- **THEN** no review runs until the pull request is marked ready for review.

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

### Scenario: a writer assigns a pull request

- **WHEN** a writer assigns a reviewed pull request
- **THEN** no run of the workflow starts.

### Scenario: a reviewer is requested

- **WHEN** a writer requests a reviewer on a pull request, or removes that
  request
- **THEN** no run of the workflow starts.

### Scenario: an unrelated label is added

- **WHEN** a label other than `request-ai-review` or `resume-ai-review` is
  added while a requested
  review is queued
- **THEN** no review runs for the label, the queued review keeps its place, and
  `ai-review-present` in the label's run reports on the existing reviews.

### Scenario: a writer comments `@claude`

- **WHEN** a writer opens a pull request comment, review comment, or issue with
  `@claude`
- **THEN** no run of the workflow starts.

## Requirement: a pull request can block every AI review

While a pull request carries the `block-ai-reviews` label, no review SHALL run
for it, whatever event starts the run, an explicit `request-ai-review` or
`resume-ai-review` included. A `request-ai-review` or `resume-ai-review` added
while the block is on SHALL stay on the pull request, and removing
`block-ai-reviews` SHALL start a run that takes it. The
label SHALL NOT waive the `ai-review-present` gate.

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

### Scenario: a writer requests a review on a blocked pull request

- **WHEN** a writer adds `request-ai-review` to a pull request carrying
  `block-ai-reviews`
- **THEN** no review runs, and `request-ai-review` stays on the pull request.

### Scenario: the block is lifted with a request waiting

- **WHEN** `block-ai-reviews` is removed from a pull request carrying
  `request-ai-review`
- **THEN** a run reviews the pull request, and its review job then removes
  `request-ai-review`.

### Scenario: a writer requests a resume on a blocked pull request

- **WHEN** a writer adds `resume-ai-review` to a pull request carrying
  `block-ai-reviews`
- **THEN** no review runs, and `resume-ai-review` stays on the pull request until
  removing `block-ai-reviews` starts a run that takes it.
```

## Depends on

- [The AI responder posts as the plume-works-quill
  App](20261030-responder-quill-app-identity.md)
- [Request and block AI reviews with labels](20261108-label-review-triggers.md)

## Verification

- `uv run pytest .github/actions/run-claude-responder/test_session_state.py`
- `uv run validate_agent_files --recommend . --require-marketplace claude`
- `uv run pre-commit run actionlint --all-files`
- `uv run pre-commit run zizmor --all-files`
- `iwe normalize`
- `iwe schema validate`
- Review the external CI evidence from Task 7 for session identity, head-SHA
  validation, refusal comments, label removal, one submitted review, and the
  final gate result.

## Out of scope

- Automatically scheduling or retrying a review when Claude quota resets.
- A `request-review.py` option or skill flow that adds `resume-ai-review`; a
  writer adds it by hand.
- Sharing review sessions across multiple self-hosted runner machines.
- Persisting credentials, settings, plugin registries, or the complete Claude
  home directory.
- Recovering a process killed before Claude produced an execution file and the
  responder recorded its session metadata.
- Provisioning, patching, monitoring, or backing up the self-hosted runner host.
- Implementing transcript garbage collection or runner-volume capacity
  management beyond Claude's configured retention behavior.
- General checkpointing or sharding of individual review passes independently of
  Claude's session transcript.

## Key references

- `.github/workflows/ai-responder.yml#on.pull_request.types › "labeled"` —
  `labeled` among the `pull_request` trigger types
- `.github/workflows/ai-responder.yml#concurrency` — workflow concurrency group;
  `.github/workflows/ai-responder.yml#concurrency.cancel-in-progress` —
  `cancel-in-progress` only on `synchronize`
- `.github/workflows/ai-responder.yml#jobs.preflight.if` — preflight runs only
  for routed label events
- `.github/workflows/ai-responder.yml#jobs.preflight.outputs` — preflight
  outputs;
  `.github/workflows/ai-responder.yml › "label.name === 'block-ai-reviews'"` —
  live label read
- `.github/workflows/ai-responder.yml › "const wantsReview"` — `wantsReview`
- `.github/workflows/ai-responder.yml#jobs.claude-respond` — `claude-respond`
  job; `.github/workflows/ai-responder.yml#jobs.claude-respond.runs-on` — its
  `runs-on`
- `.github/workflows/ai-responder.yml#jobs.ai-review-present` —
  `ai-review-present`
- `.github/actions/run-claude-responder/action.yml#inputs` — composite action
  inputs;
  `.github/actions/run-claude-responder/action.yml#inputs.remove-request-label`
  — `remove-request-label`
- `.github/actions/run-claude-responder/action.yml › "id: claude_args"` —
  `claude_args` assembly
- `.github/actions/run-claude-responder/action.yml › "id: claude_responder"` —
  Claude invocation
- `.github/actions/run-claude-responder/action.yml › "name: Take the review request label"`
  — "Take the review request label"
- `.github/actions/run-claude-responder/action.yml › "uses: actions/upload-artifact@v7.0.2"`
  — execution output upload
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md#steps › "Run the independent initial-review passes the effort"`
  — parallel review passes
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md#steps › "create_pending_pull_request_review"`
  — pending-review creation
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md#waiting-on-parallel-passes`
  — Waiting on Parallel Passes
- `.github/workflows/validate-agent-files.yml#jobs.validate-agent-files` —
  agent-file validation job
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md#ai-responder-and-the-review-gate`
  — the review labels prerequisite
- `docs/knowledge/data/spec/ai-review-gate.md#requirement-a-review-runs-on-first-push-and-on-explicit-request`
  — the review-request requirement;
  `docs/knowledge/data/spec/ai-review-gate.md#requirement-a-pull-request-can-block-every-ai-review`
  — the block requirement
- `docs/knowledge/data/features/ai-responder-workflows.md#behaviour › "is the author's call: adding the"`
  — review requests by label
