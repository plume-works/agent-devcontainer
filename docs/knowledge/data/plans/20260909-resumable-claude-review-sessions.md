---
type: plan
created: 2026-09-09
description: Resume an interrupted Claude pull-request review from a persistent local session after an explicit review-resume comment.
generated:
  by: codex/gpt-5
  at: 2026-09-09T23:48:39Z
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

The approved trigger is an exact match after trimming surrounding whitespace;
ordinary `@claude review` remains a fresh review. A resume starts only from the
exact resume trigger; automatic waiting and scheduled retries are out of scope.

The rejected alternative is uploading and restoring the whole Claude home as an
artifact. It duplicates state already available on the selected persistent
runner, increases secret exposure, and adds artifact download orchestration.
Persisting only the execution output is also rejected because it is not the
transcript format consumed by `--resume`.

The runner host registration, operating-system maintenance, and creation of the
`claude-review` environment remain external administration. The repository
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

### Task 3: Route and validate the explicit resume request

**Files:** Modify: `.github/workflows/ai-responder.yml`,
`.github/actions/run-claude-responder/action.yml`

- [ ] Preserve and recognize this approved trigger verbatim after trimming
  surrounding whitespace:

  ``` text
  @claude review resume
  ```

- [ ] Extend the comment bridge and `workflow_dispatch` inputs/outputs so the
  exact trigger remains a review request while carrying an explicit resume flag
  to `claude-respond`; do not classify it as a free-form task or make ordinary
  review requests resumptions.

- [ ] Before invoking Claude for a resume, resolve the previous attempt and also
  refuse when an accepted AI review already exists. On any refusal, post exactly
  one top-level operational comment naming the reason and current run, then fail
  without invoking Claude. This comment is workflow diagnostics, not a review
  finding.

- [ ] For valid state, pass the resolved session ID through the responder's
  `claude_args` as `--resume` and replace the fresh-review request with a
  continuation instruction that says prior background processes are gone,
  incomplete passes must be relaunched, and completed work must not be
  duplicated.

- [ ] Keep the current fork, writer-authorization, immutable-head checkout,
  content-permission, and `ai-review-present` gates in force for resume
  dispatches.

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

- [ ] Record the session-state boundary, dedicated-runner decision, volume
  contents, metadata key, validation order, concurrency rule, retention
  ownership, and rejected artifact/full-home alternatives in the architecture
  graph.
- [ ] Update the feature description to include explicit, validated review
  continuation without weakening the existing review gate.
- [ ] Add the dedicated `claude-review` self-hosted runner and its Docker daemon
  as required external prerequisites in the template-consumption guide, and tell
  consumers that keep the responder workflow to adapt the label and persistence
  policy to their infrastructure.

### Task 6: Prove continuation on the dedicated runner

**Files:** External configuration and GitHub Actions evidence only

- [ ] Register exactly one persistent runner with the `self-hosted` and
  `claude-review` labels and a Docker daemon that retains the named volume
  between jobs.
- [ ] Produce an interrupted review attempt that records a session, then comment
  with the approved resume trigger after capacity is available; verify the next
  job selects the prior run automatically, uses the same session ID and head
  SHA, continues the review, submits no duplicate review, and satisfies
  `ai-review-present`.
- [ ] Exercise no-record and changed-head refusals; verify each skips Claude,
  fails loudly, and posts exactly one reason-bearing PR comment.

## Spec changes

[AI review gate](../spec/ai-review-gate.md):

``` markdown
## ADDED Requirements

### Requirement: interrupted Claude reviews resume only from valid persistent state

An authorized writer's pull-request comment whose body, after trimming
surrounding whitespace, is exactly `@claude review resume` SHALL dispatch a
review-resume run on the pull request's head branch. The responder SHALL select
the latest prior Claude review attempt recorded for that repository and pull
request and SHALL invoke Claude with `--resume` only when the attempt is
incomplete, its session transcript exists unambiguously, no accepted AI review
already exists, and its recorded head SHA equals the current pull-request head.

Every Claude review attempt that initializes a session and produces execution
output SHALL atomically record its run ID, pull-request number, head SHA,
session ID, conclusion, and transcript location in persistent runner-local
state before the job exits. A valid resumed attempt SHALL preserve all existing
fork, requester-authorization, immutable-checkout, permission, and review-gate
controls.

#### Scenario: an interrupted review is resumed

- **WHEN** a writer comments `@claude review resume`, the latest prior review
  attempt is incomplete, its transcript is available, its head SHA is current,
  and no accepted AI review exists
- **THEN** the workflow resumes that session, recovers completed pass results,
  relaunches work whose background process was lost, and submits at most one
  pull-request review.

#### Scenario: no prior review attempt exists

- **WHEN** a writer comments `@claude review resume` and no prior review attempt
  is recorded for that pull request
- **THEN** Claude is not invoked, the review job fails, and the workflow posts
  exactly one pull-request comment naming the missing prior attempt and the
  failed run.

#### Scenario: the pull-request head changed

- **WHEN** the selected prior attempt's recorded head SHA differs from the
  current pull-request head
- **THEN** Claude is not invoked, the review job fails, and the workflow posts
  exactly one pull-request comment naming the stale-head refusal and the failed
  run.

#### Scenario: prior session state is unusable

- **WHEN** the selected attempt is completed, its metadata or session ID is
  invalid, or its transcript is missing or ambiguous
- **THEN** Claude is not invoked, the review job fails, and the workflow posts
  exactly one pull-request comment naming the refusal and the failed run.

#### Scenario: a review already exists

- **WHEN** the pull request already has an accepted AI review when a resume is
  requested
- **THEN** Claude is not invoked, the review job fails, and the workflow posts
  exactly one pull-request comment stating that there is no incomplete review
  to resume.

#### Scenario: an ordinary review is requested

- **WHEN** a writer comments `@claude review`
- **THEN** the workflow starts a fresh review session and does not select or
  resume stored session state.
```

## Verification

- `uv run pytest .github/actions/run-claude-responder/test_session_state.py`
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
- `uv run pre-commit run actionlint --all-files`
- `uv run pre-commit run zizmor --all-files`
- `iwe normalize`
- `iwe schema validate`
- Review the external CI evidence from Task 6 for session identity, head-SHA
  validation, refusal comments, one submitted review, and the final gate result.

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

Verified anchor points (line numbers as of 2026-09-09):

- `.github/workflows/ai-responder.yml:33` — `workflow_dispatch` inputs
- `.github/workflows/ai-responder.yml:64` — workflow concurrency policy
- `.github/workflows/ai-responder.yml:118` — preflight outputs
- `.github/workflows/ai-responder.yml:229` — `Determine agent prompts`
- `.github/workflows/ai-responder.yml:323` — pull-request comment bridge
- `.github/workflows/ai-responder.yml:377` — `claude-respond` job
- `.github/actions/run-claude-responder/action.yml:4` — composite action inputs
- `.github/actions/run-claude-responder/action.yml:115` — Claude invocation
- `.github/actions/run-claude-responder/action.yml:129` — always-uploaded
  execution output
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:96` — parallel review
  passes
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:103` — outstanding-pass
  barrier
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:106` — pending-review
  creation
- `.github/workflows/validate-agent-files.yml:61` — agent-file validation job
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:374`
  — AI responder prerequisites
- `docs/knowledge/data/spec/ai-review-gate.md:111` — comment-dispatch
  requirement
- `docs/knowledge/data/features/ai-responder-workflows.md:30` — responder
  behavior
