---
type: plan
created: 2026-09-09
release:
- features/ai-responder-workflows
description: Resume an interrupted Claude pull-request review from a persistent local session when a writer adds the one-shot ai-review-resume label.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T21:30:00Z
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
rank: 1100
---

# Resume interrupted Claude PR reviews on a persistent runner

## Context

The [AI responder workflow](../features/ai-responder-workflows.md) runs each
Claude review in a disposable job container. A long review can therefore reach a
usage limit after substantial work, while the next job has neither the local
Claude transcript nor a supported way to continue it.

The responder uploads its execution file when one is available after execution.
Resumption also requires the corresponding persistent transcript tree and
session identifier.

Re-reviews are requested by assigning the pull request, because only a
`pull_request`-event run's `ai-review-present` counts toward merge ([Assignee-
triggered AI re-reviews](../architecture/assignee-review-trigger.md)). A resume
request follows the same rule, so it is a pull-request label, not a comment.

Once [The AI responder posts as the plume-works-quill
App](20261030-responder-quill-app-identity.md) lands, the review job runs in the
`plume-works-review` environment and posts as the `plume-works-quill` App, with
an installation token minted inside `run-claude-responder` after the
devcontainer lifecycle scripts. A resume run inherits that identity and token
flow unchanged.

## Approach

Run only the `claude-respond` job on one persistent self-hosted runner carrying
the custom label `claude-review`. Mount a runner-local named Docker volume,
`agentdev-claude-review-sessions`, at `/github/home/.claude/projects` inside
every review job container. This keeps Claude's transcripts and subagent
transcript tree across disposable containers without persisting its credentials,
settings, or plugin registry. The task responder and non-agent jobs remain on
their current hosted runners.

Each initialized review attempt records an atomic, repository-and-PR-scoped
`latest` metadata document in that volume containing its run ID, head SHA,
session ID, conclusion, and transcript location. A resume request selects that
latest prior attempt automatically. Before Claude starts, it rejects missing,
malformed, completed, transcript-less, or head-mismatched state, posts one
operational PR comment explaining the rejection, and fails the review job. A
valid attempt passes the stored session ID to Claude with `--resume` and a
continuation prompt that accounts for background agents lost with the prior
process.

A writer requests a resume by adding the `ai-review-resume` label. That fires
`pull_request`/`labeled`, a run whose gate counts, so a resumed review holds and
clears the merge as an assigned re-review does. The run removes the label once
it has accepted or refused the request, so one label adds one attempt. Adding
any other label runs no job and stays out of the `pr-<n>` concurrency group, so
it cannot displace a queued review. A re-request by assignment remains a fresh
review; a resume starts only from the label, and automatic waiting and scheduled
retries are out of scope.

Rejected alternatives: a `@claude review resume` comment, because a dispatched
run's gate does not count toward merge; a body marker read on re-assignment,
because a marker stays in the body and turns every later re-review into a resume
attempt; uploading and restoring the whole Claude home as an artifact, which
duplicates state already on the persistent runner, increases secret exposure,
and adds artifact download orchestration; and persisting only the execution
output, which is not the transcript format `--resume` consumes.

Registering the runner host with the `claude-review` label and its
operating-system maintenance remain external administration. The
`plume-works-review` GitHub environment and the App secrets it holds are the
dependency's prerequisites; the self-hosted runner receives them for each review
job as a hosted runner does. The persistent volume holds only
`.claude/projects`, so neither the App private key nor a minted token outlives
the job container. The repository declares the required runner label and Docker
volume; the implementation is not complete until a CI run proves that external
prerequisite.

The workflow keeps one latest-attempt metadata pointer per repository and pull
request and never deletes Claude-owned transcript files. Claude's configured
transcript retention and the runner administrator own garbage collection and
volume capacity; the resume workflow only reads and writes its namespaced
metadata.

## Implementation Steps

### Task 1: Give review containers a persistent Claude transcript store

**Files:** Modify: `.github/workflows/ai-responder.yml`

- [ ] Route `claude-respond` to `[self-hosted, claude-review]`, leaving
  `claude-task`, preflight, bridge, and gate runner selection unchanged.
- [ ] Mount the named Docker volume `agentdev-claude-review-sessions` at
  `/github/home/.claude/projects` in the review job container, keeping the
  remainder of Claude's home disposable.
- [ ] Serialize review jobs that can address the same PR session so a fresh or
  resumed attempt cannot mutate one session concurrently with another.

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

### Task 3: Route and validate the label request

**Files:** Modify: `.github/workflows/ai-responder.yml`,
`.github/actions/run-claude-responder/action.yml`

- [ ] `labeled` joins the `pull_request` trigger types. A `labeled` event for
  any label other than `ai-review-resume` runs no job and takes a concurrency
  group of its own, so it never replaces a pending run in `pr-<n>`.
- [ ] Preflight treats a `labeled` event for `ai-review-resume` as a review
  request carrying a resume flag to `claude-respond`, under the same
  skip-marker, draft, fork, bot-author, and writer-authorization checks as
  `assigned`, with the person who added the label as the requester.
- [ ] The run removes the `ai-review-resume` label once preflight has accepted
  or refused the request, from a job holding only the permission that removing a
  label needs.
- [ ] Before invoking Claude for a resume, resolve the previous attempt and also
  refuse when an accepted AI review already exists. On any refusal, post exactly
  one top-level operational comment, as the App with the job's minted token,
  naming the reason and current run, then fail without invoking Claude. This
  comment is workflow diagnostics, not a review finding.
- [ ] For valid state, pass the resolved session ID through the responder's
  `claude_args` as `--resume` and replace the fresh-review request with a
  continuation instruction that says prior background processes are gone,
  incomplete passes must be relaunched, and completed work must not be
  duplicated.
- [ ] Keep the current fork, writer-authorization, immutable-head checkout,
  content-permission, and `ai-review-present` gates in force for resume runs.

### Task 4: Make the review skill safe after process loss

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

- [ ] Define resumed-run handling: reuse pass results already returned in the
  transcript, treat prior outstanding task IDs as dead, relaunch only incomplete
  initial or validation passes, and apply the blocking-wait rule only to tasks
  created by the current process.
- [ ] Define idempotent review publication: if interruption left an unsubmitted
  pending review, discard and reconstruct it from the validated findings before
  one final submission; if an accepted review already exists, publish nothing
  further.

### Task 5: Record the runner boundary and consumer adaptation

**Files:** Create:
`docs/knowledge/data/architecture/resumable-ai-review-sessions.md`; Modify:
`docs/knowledge/data/architecture.md`,
`docs/knowledge/data/features/ai-responder-workflows.md`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [ ] Record the session-state boundary, dedicated-runner decision, label
  trigger, volume contents, metadata key, validation order, concurrency rule,
  retention ownership, and rejected comment, body-marker, artifact, and
  full-home alternatives in the architecture graph.
- [ ] Update the feature description to include explicit, validated review
  continuation by label without weakening the existing review gate.
- [ ] Add the dedicated `claude-review` self-hosted runner, its Docker daemon,
  and the `ai-review-resume` label as required external prerequisites in the
  template-consumption guide, beside the App and `plume-works-review`
  environment the dependency documents, and tell consumers that keep the
  responder workflow to adapt the runner label and persistence policy to their
  infrastructure.

### Task 6: Prove continuation on the dedicated runner

**Files:** External configuration and GitHub Actions evidence only

- [ ] Register exactly one persistent runner with the `self-hosted` and
  `claude-review` labels and a Docker daemon that retains the named volume
  between jobs.
- [ ] Produce an interrupted review attempt that records a session, then add the
  `ai-review-resume` label after capacity is available; verify the next job
  selects the prior run automatically, uses the same session ID and head SHA,
  continues the review, submits no duplicate review, removes the label, and
  satisfies `ai-review-present`.
- [ ] Add the label on a pull request with no recorded attempt; verify the run
  skips Claude, fails, posts exactly one reason-bearing comment, and removes the
  label.
- [ ] Add the label after the head changed since the recorded attempt; verify
  the run skips Claude, fails, posts exactly one reason-bearing comment, and
  removes the label.

## Spec changes

[AI review gate](../spec/ai-review-gate.md):

``` markdown
## ADDED Requirements

### Requirement: interrupted Claude reviews resume only from valid persistent state

A writer adding the `ai-review-resume` label to a pull request SHALL start a
review-resume run from that `pull_request` `labeled` event, whose
`ai-review-present` counts toward merge, and the run SHALL remove the label once
it accepts or refuses the request. The responder SHALL select the latest prior
Claude review attempt recorded for that repository and pull request and SHALL
invoke Claude with `--resume` only when the attempt is incomplete, its session
transcript exists unambiguously, no accepted AI review already exists, and its
recorded head SHA equals the current pull-request head. Adding any other label
SHALL NOT run a review or displace a pending responder run.

Every Claude review attempt that initializes a session and produces execution
output SHALL atomically record its run ID, pull-request number, head SHA,
session ID, conclusion, and transcript location in persistent runner-local
state before the job exits. A resume run SHALL preserve all existing fork,
requester-authorization, immutable-checkout, permission, and review-gate
controls.

#### Scenario: an interrupted review is resumed

- **WHEN** a writer adds the `ai-review-resume` label, the latest prior review
  attempt is incomplete, its transcript is available, its head SHA is current,
  and no accepted AI review exists
- **THEN** the workflow resumes that session, recovers completed pass results,
  relaunches work whose background process was lost, submits at most one
  pull-request review, and removes the label.

#### Scenario: no prior review attempt exists

- **WHEN** a writer adds the `ai-review-resume` label and no prior review
  attempt is recorded for that pull request
- **THEN** Claude is not invoked, the review job fails, the label is removed,
  and the workflow posts exactly one pull-request comment naming the missing
  prior attempt and the failed run.

#### Scenario: the pull-request head changed

- **WHEN** the selected prior attempt's recorded head SHA differs from the
  current pull-request head
- **THEN** Claude is not invoked, the review job fails, the label is removed,
  and the workflow posts exactly one pull-request comment naming the stale-head
  refusal and the failed run.

#### Scenario: prior session state is unusable

- **WHEN** the selected attempt is completed, its metadata or session ID is
  invalid, or its transcript is missing or ambiguous
- **THEN** Claude is not invoked, the review job fails, the label is removed,
  and the workflow posts exactly one pull-request comment naming the refusal and
  the failed run.

#### Scenario: a review already exists

- **WHEN** the pull request already has an accepted AI review when a resume is
  requested
- **THEN** Claude is not invoked, the review job fails, the label is removed,
  and the workflow posts exactly one pull-request comment stating that there is
  no incomplete review to resume.

#### Scenario: a writer re-requests a review by assignment

- **WHEN** a writer removes the pull request's author as assignee and adds them
  back
- **THEN** the workflow starts a fresh review session and does not select or
  resume stored session state.

#### Scenario: another label is added

- **WHEN** a label other than `ai-review-resume` is added while an assigned
  review waits in the pull request's concurrency group
- **THEN** no review runs for the label and the waiting review still runs.
```

## Depends on

- [The AI responder posts as the plume-works-quill
  App](20261030-responder-quill-app-identity.md)

## Verification

- `uv run pytest .github/actions/run-claude-responder/test_session_state.py`
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
- `uv run pre-commit run actionlint --all-files`
- `uv run pre-commit run zizmor --all-files`
- `iwe normalize`
- `iwe schema validate`
- Review the external CI evidence from Task 6 for session identity, head-SHA
  validation, refusal comments, label removal, one submitted review, and the
  final gate result.

## Out of scope

- Automatically scheduling or retrying a review when Claude quota resets.
- Resuming free-form `claude-task` sessions.
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

Verified anchor points (line numbers as of 2026-10-30):

- `.github/workflows/ai-responder.yml:19` — `pull_request` trigger types
- `.github/workflows/ai-responder.yml:67` — workflow concurrency group; `:75` —
  `cancel-in-progress` only on `synchronize`
- `.github/workflows/ai-responder.yml:118` — preflight outputs
- `.github/workflows/ai-responder.yml:185` — the `[ci:skip-ai-review]` marker
- `.github/workflows/ai-responder.yml:236` — `Determine agent prompts`; `:267` —
  the actions that always review, `assigned` among them
- `.github/workflows/ai-responder.yml:414` — `claude-respond` job
- `.github/workflows/ai-responder.yml:502` — `ai-review-present`
- `.github/actions/run-claude-responder/action.yml:4` — composite action inputs
- `.github/actions/run-claude-responder/action.yml:132` — `claude_args` assembly
- `.github/actions/run-claude-responder/action.yml:150` — Claude invocation
- `.github/actions/run-claude-responder/action.yml:163` — execution output
  upload
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:126` — parallel review
  passes
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:159` — Waiting on Parallel
  Passes, the outstanding-pass barrier
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:147` — pending-review
  creation
- `.github/workflows/validate-agent-files.yml:61` — agent-file validation job
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:373`
  — AI responder prerequisites
- `docs/knowledge/data/spec/ai-review-gate.md:88` — the review-request
  requirement; `:105` — the re-request-by-assignment scenario
- `docs/knowledge/data/features/ai-responder-workflows.md:75` — re-review by
  assignment
