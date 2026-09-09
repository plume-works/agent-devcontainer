---
type: plan
description: The hook-driven experiential-learning MVP and its pty wake harness, as implemented in the merge source before consolidation.
created: 2026-09-09
generated:
  by: claude-code/opus-5
  at: 2026-09-09T00:00:00Z
sources:
- resource: https://github.com/plume-works/agent-self-improvement
  title: agent-self-improvement at e94031a, specs 0001 and 0002
stage: done
completed: 2026-08-02
---

# Self-improve MVP

## Context

The plugin was designed and built in `plume-works/agent-self-improvement` and
arrived here complete, as
[Consolidate the self-improve plugin into this repository](20260909-consolidate-self-improve-plugin.md)
records. This plan is the transcription of that work: it is filed `done` because
the behavior shipped before the move, and it exists so the graph carries the
acceptance record rather than only the code.

The durable behavior is
[Self-improve learning loop](../spec/self-improve-learning-loop.md); the runtime
decisions are [Self-improve runtime](../architecture/self-improve-runtime.md).
This plan records what was accepted and on what evidence.

It absorbs two specifications from the merge source: the MVP itself, and the
pseudo-terminal harness that verifies the one behavior the headless suite cannot
observe. They are one plan here because the harness exists only to close the
MVP's tenth acceptance criterion, and neither is separately shippable.

## Approach

Package a narrowed reviewer as a Claude Code plugin and invoke it through
supported lifecycle hooks, in four slices: a packaged manual tracer bullet, then
deterministic event capture, then automatic asynchronous review behind the
`Stop` hook, then packaged acceptance against a clean Claude home.

The reviewer is an independent, tool-free Claude call rather than the existing
interactive `/improve` workflow, which scans broad configuration and historical
state, launches multiple agents, and can mutate several artifact classes
directly.

## Implementation Steps

### Task 1: Packaged manual tracer bullet

**Files:** Create:
`.agents/plugins/self-improve/{.claude-plugin,skills,scripts,reviewer}/**`

- [x] Package the plugin and its `improve` command, run the isolated reviewer
  against a redacted current-turn bundle, stage one exact proposal, and exercise
  authorization, atomic application, fresh-session discovery, and rollback.
  - **Evidence:** merge source `e94031a`; the offline suite covering these paths
    passes in this repository as part of `make test` (825 passed, 14 skipped).

### Task 2: Deterministic event capture

**Files:** Create:
`.agents/plugins/self-improve/selfimprove/{capture,gate,redact}.py`

- [x] Add `UserPromptSubmit`, `PostToolUseFailure`, and `PostToolUse` capture
  with event schemas, redaction, expiry, deduplication, and meaningful-event
  unit tests, with automatic model invocation still disabled.
  - **Evidence:** merge source `e94031a`; the gate, redaction, and capture unit
    tests pass in this repository under `make test`.

### Task 3: Automatic asynchronous review

**Files:** Create: `.agents/plugins/self-improve/selfimprove/orchestrate.py`;
Modify: `.agents/plugins/self-improve/hooks/hooks.json`

- [x] Add the guarded `Stop` hook with `asyncRewake`, invoking the reviewer only
  when the deterministic gate passes and waking the session only for a valid,
  non-duplicate candidate.
  - **Evidence:** merge source `e94031a`; the recursion, `stop_hook_active`, and
    wake-only-for-valid-candidate guards are covered by the integration suite,
    which passes under `make test`.

### Task 4: Packaged acceptance

**Files:** Create: `.agents/plugins/self-improve/tests/smoke/**`

- [x] Install the built plugin into a clean test Claude home and exercise
  correction, failure-to-success, no-signal, rejection, approval, stale-target,
  restart, and rollback, verifying a fresh session discovers the result.
  - **Evidence:** merge source `e94031a`; nine of the ten packaged smoke checks
    observed passing against a real Claude Code session on 2026-08-02. The tenth
    is the asynchronous wake, closed by Task 5.

### Task 5: Automated wake verification on a pseudo-terminal

**Files:** Create: `.agents/plugins/self-improve/tests/smoke/pty_harness.py`,
`.agents/plugins/self-improve/tests/smoke/test_wake_pty.py`

- [x] Drive a real session on a pty, assert on plugin-controlled state and one
  plugin-controlled marker, and demonstrate the harness fails when the wake does
  not arrive.
  - **Evidence:** merge source `e94031a`; both live checks observed passing
    together on 2026-08-01 against Claude Code 2.1.220 — the wake arrived at an
    idle session for `cand-12f3c9117d4c`, and the negative control stored
    `cand-d5552db5fde5` and saw no wake with `asyncRewake` disabled.
    `make wake-repeat` then completed ten consecutive runs with no failure on
    2026-08-02. The model-free harness self-checks pass in this repository:
    `make test-harness`, 10 passed.

## Outstanding work

**Wake-harness acceptance criterion 6.1 is not met.** It asks for an arriving
wake *detected* in ten consecutive runs. `make wake-repeat` completed ten runs
with no failure, but nine of the ten reached the assertion: one wake check
skipped on a review that stored no candidate to watch for. Five of the twenty
checks across those runs skipped for that reason; the other four were the
negative control, carried as
[Reviewer decline asymmetry](../bugs/self-improve-reviewer-decline-asymmetry.md).

Closing it requires ten runs in which every wake check reaches its assertion,
which costs real model usage. Only someone willing to spend that can close it.

The other four criteria — failing when the wake genuinely does not arrive,
asserting only on plugin-controlled surfaces, leaving one inspectable directory
per run, and running behind its own target — have been observed.

## Spec changes

None by this plan. It transcribes behavior that shipped in the merge source;
[Self-improve learning loop](../spec/self-improve-learning-loop.md) records that
behavior as it arrived, adding, modifying, and removing no requirement.

## Verification

- `make test` passes with no live test collected.
- `make test-harness` passes, spending no model usage.
- `make wake` observes an arriving wake and its negative control — costs model
  usage, and is what criterion 6.1 needs ten clean runs of.

## Out of scope

- A prompt optimizer, user-authored evaluation datasets, or model-generated
  rubrics treated as proof of improvement.
- Full `/improve` scans per turn, and broad or unattended transcript harvesting.
- Automatic adoption of model-authored changes, and autonomous edits to
  Claude-managed auto-memory.
- Multi-artifact restructuring, deletion, or semantic consolidation.
- Long-term usage scoring and stale-skill curation.
- Certification for VS Code, Desktop, SSH, devcontainer, cloud, or multi-user
  surfaces.
- Daemon, federation, vector-memory, or model-weight infrastructure.
