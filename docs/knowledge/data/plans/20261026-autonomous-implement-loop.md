---
type: plan
created: 2026-10-26
description: Have the Implement orchestrator dispatch iwe-verifier after the tasks, act on its findings, and revise its own plan through the iwe-planner rulebook once a fresh-context iwe-revision-evaluator approves, escalating only narrowing, release, and approved-text changes to the user.
release:
- features/autonomous-implement-loop
- features/verification-in-the-main-loop
generated:
  by: claude-code/opus-5.5
  at: 2026-10-26T05:00:00Z
sources:
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
- resource: scripts/e2e/iwe-workflows/clone.py
---

# Let Implement verify, fix, and revise on its own

## Context

[Let Implement verify, fix, and revise on its
own](../backlog/autonomous-implement-loop.md) is the backlog task this plan
replaces, and [Autonomous Implement
loop](../features/autonomous-implement-loop.md) is the behavior it builds. Today
Implement ends by suggesting `/agentdev:iwe-verify` and stops for the user at
every material deviation. The maintainer decided Implement should run Verify
itself, act on the report, and revise its plan without them once an independent
evaluation approves the revision.

That reverses a recorded decision in [Verification in the main
loop](../features/verification-in-the-main-loop.md): "Implement does not gain a
second automatic invocation". The feature is listed in `release` because its
behavior changes.

The maintainer settled four choices:

- The evaluator may approve any revision except one that drops, narrows, defers,
  or accepts an exception to specified behavior, changes `release`, or changes
  text the user approved.
- Implement acts on every CRITICAL and every WARNING with a concrete route.
- The run stops when a finding recurs after a fix attempt, and in any case after
  3 Verify rounds or 1 approved revision.
- `/agentdev:iwe-implement-all` gets the loop in this plan too.

## Approach

**One orchestrator runs the loop, and every agent is a leaf.** The user's
session runs it for `/agentdev:iwe-implement`; the coordinator runs it for
`/agentdev:iwe-implement-all`, once per plan. `iwe-implementer`, `iwe-verifier`,
and the new `iwe-revision-evaluator` never dispatch. That holds on all three
harnesses without OpenCode's experimental depth setting ([Nested subagent
dispatch](../architecture/nested-subagent-dispatch.md)).

**The loop lives once, in the `iwe-implementer` rulebook,** as a section that
only an orchestrator runs. The session already follows the rulebook in place.
The coordinator reads the same file for that section, so the two never drift. A
dispatched Implementer that hits a material deviation still stops and reports
it, and the coordinator takes the revision route.

**Revision rules come from a new `iwe-planner` agent file.**
`/agentdev:iwe-plan` is explicit-only, and reading a gated skill's file to get
around the gate is rejected in [Explicit-only workflow
agents](../architecture/explicit-only-workflow-agents.md). So the Plan rulebook
moves into `iwe-planner`, which `/agentdev:iwe-plan` follows in place — the
Implement pattern. The orchestrator follows its revise mode, never its create
mode, so `close-issue.sh` stays bundled with the skill, which is the only route
into create mode.

**The order is draft, audit, evaluate, commit.** The orchestrator drafts the
revision under the `iwe-planner` revise rules, including the Durable Knowledge
Auditor gate and validation, and leaves it uncommitted. The evaluator then
judges the final text. Its prompt carries the plan key and the finding the
revision answers, quoted as reported, and nothing else. It reads the plan at
`HEAD` and the uncommitted diff, and returns one of three verdicts:

- `APPROVE` — the revision answers the finding and keeps the plan's outcome. The
  orchestrator commits it and resumes.
- `REJECT` — the revision restates the plan to match the code or does not answer
  the finding.
- `ESCALATE` — the revision falls in the always-escalate list.

On `REJECT` or `ESCALATE` the orchestrator restores the plan file from `HEAD`
and stops with a report.

Rejected:

- **Let `iwe-verifier` judge the revision.** Verify checks code against the
  plan. The revision question is whether the new plan still serves the old one's
  outcome, so it needs a separate agent with its own rubric.
- **Reuse `Principal Engineer` as the evaluator.** It is advisory and can
  dispatch agents. The gate needs a leaf that returns a fixed verdict.
- **Evaluate before the audit.** The audit may rewrite the text, so the
  evaluator would have approved bytes that never landed.
- **Run the loop inside a dispatched `iwe-implementer`.** It would need nested
  dispatch, and a coordinator could then no longer see what its Implementer
  dispatched.

## Implementation Steps

### Task 1: Move the Plan rulebook into iwe-planner

**Files:** Create: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`;
Modify: `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md`

- [x] Create `iwe-planner.agent.md` holding the skill's Steps,
  `## Closing the issue`, `## The three forms of ## Spec changes`, and Rules,
  unchanged in what they require. Its tools are
  `Bash, Read, Edit, Write, Grep, Glob, Skill`. Its `description` says it is
  followed in place by the `iwe-plan` skill and by the Implement orchestrator
  applying a revision, and is never dispatched or started on a description
  match.
  - **Evidence:** commit "Move the Plan rulebook into iwe-planner"; the moved
    sections differ from the old skill only by the close-issue script location
    sentence;
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    reports 0 errors, and `uv run pytest .agents/plugins/agentdev/tests` passes
    270\.
- [x] Add a `## How you run` section with two modes. **From
  `/agentdev:iwe-plan`** is today's behavior: create or revise, asking the user.
  **From the Implement orchestrator** is revise mode only: it drafts the
  revision, runs the audit and validation, and stops uncommitted for the
  evaluator. It never creates a plan, closes an issue, or re-dispatches the
  Shipper. The issue-closing step names the script as the `iwe-plan` skill's
  bundled `agent-code/close-issue.sh`.
  - **Evidence:** commit "Move the Plan rulebook into iwe-planner" adds
    `## How you run` to `iwe-planner.agent.md` with both modes and the
    close-issue script location in step 8; the validator reports 0 errors.
- [x] Reduce `iwe-plan/SKILL.md` to following
  `../../agents/iwe-planner.agent.md` in place in its **From
  `/agentdev:iwe-plan`** mode, keeping the skill's frontmatter, `allowed-tools`,
  and `agent-code/`.
  - **Evidence:** commit "Move the Plan rulebook into iwe-planner"; the skill
    keeps its frontmatter, `allowed-tools`, `agents/openai.yaml`, and
    `agent-code/`, and `test_catalog_gates_agree` passes in the 270-test run.

### Task 2: Create the iwe-revision-evaluator agent

**Files:** Create:
`.agents/plugins/agentdev/agents/iwe-revision-evaluator.agent.md`

- [x] Write the agent with tools `Bash, Read, Grep, Glob`. Its `description`
  says it is dispatched only by the Implement orchestrator, never on a
  description match. Its inputs are the plan key and the quoted finding, and any
  other prompt content is not evidence. It reads the plan with
  `git show HEAD:<path>` and `git diff -- <path>`. It returns `APPROVE`,
  `REJECT`, or `ESCALATE` on the first line, with reasons citing the diff's
  lines.
  - **Evidence:** commit "Add the iwe-revision-evaluator agent";
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    reports 0 errors, and `install-codex-agents.py` writes
    `agentdev-iwe-revision-evaluator.toml` with `sandbox_mode = "read-only"`.
- [x] State the rubric. `ESCALATE` covers every item on the always-escalate list
  in `## Context`. `REJECT` covers a revision that does not answer the quoted
  finding, or one that rewrites intent to describe the code instead of the
  outcome. `APPROVE` covers everything else: a corrected anchor or task
  breakdown, an added task or requirement, a heavier `## Spec changes` form, or
  a corrected verification step, each keeping every specified behavior.
  - **Evidence:** commit "Add the iwe-revision-evaluator agent"; `## Rubric` in
    `iwe-revision-evaluator.agent.md` lists the three verdicts with exactly
    these conditions, checked in the order ESCALATE, REJECT, APPROVE.

### Task 3: Put the loop in the iwe-implementer rulebook

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-implementer.agent.md`

- [x] Split step 7's material deviation in two. A deviation on the
  always-escalate list waits for the user, as today. Any other deviation leaves
  the task unchecked and takes the revision route. Dispatched, both stop and
  report.
  - **Evidence:** commit "Run the verify, fix, and revise loop from the
    Implement orchestrator"; step 7 of `iwe-implementer.agent.md` routes
    **Always-escalate** to the user and **Any other material deviation** to the
    revision route, and both stop when dispatched; the validator reports 0
    errors.
- [x] Add a `## Running the loop` section that only an orchestrator runs: the
  user's session, or the `iwe-implement-all` coordinator. It covers:
  - the `iwe-verifier` dispatch after the last task, carrying only the plan key
    and quoted approvals, with no conversation forwarded;
  - which findings to act on;
  - the code route: fix, evidence, Verify again;
  - the revision route: `iwe-planner` revise mode, then the evaluator, then
    commit or revert;
  - the stop bounds;
  - one rollup that adds each Verify verdict and each evaluator verdict.
  - **Evidence:** commit "Run the verify, fix, and revise loop from the
    Implement orchestrator"; `## Running the loop` steps 1-6 cover the Verify
    dispatch, findings to act on, the code route, the revision route, the stop
    bounds, and the one report.
- [x] Rewrite step 9 so the run hands to `## Running the loop` instead of
  suggesting `/agentdev:iwe-verify`, and update the Rules: material changes need
  the user's direction or an approved revision.
  - **Evidence:** commit "Run the verify, fix, and revise loop from the
    Implement orchestrator"; step 9 no longer names `/agentdev:iwe-verify` and
    hands a completed session run to `## Running the loop`, and `## Rules` names
    the user's direction or an evaluator-approved revision.

### Task 4: Wire the two entry skills to the loop

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md`

- [x] In `iwe-implement`, say that the session also runs `## Running the loop`.
  It asks the user only for an always-escalate deviation, a `Needs decision`, or
  a stop bound.
  - **Evidence:** commit "Wire the Implement entry skills to the loop";
    `iwe-implement/SKILL.md` names the session as orchestrator and lists the
    three cases it asks about; the validator reports 0 errors.
- [x] In `iwe-implement-all`, have the coordinator read `## Running the loop` in
  `../../agents/iwe-implementer.agent.md` and run it for each plan before the
  next. It re-dispatches `iwe-implementer` with the plan key and the findings to
  fix, quoted as reported. It re-posts each rollup with its Verify and evaluator
  verdicts.
  - **Evidence:** commit "Wire the Implement entry skills to the loop";
    `iwe-implement-all/SKILL.md` links the rulebook's `## Running the loop`,
    runs it per plan before the next dispatch, and re-posts each rollup with
    both verdict kinds; the validator reports 0 errors.

### Task 5: Cover the loop in the e2e suite

**Files:** Create:
`scripts/e2e/iwe-workflows/fixtures/plans/20261026-e2e-loop.md`,
`scripts/e2e/iwe-workflows/fixtures/plans/20261026-e2e-revise.md`; Modify:
`scripts/e2e/iwe-workflows/clone.py`, `scripts/e2e/iwe-workflows/scenarios.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_codex.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py`

- [ ] Add the loop fixture. Its one task writes `e2e/loop.txt` holding `loop`,
  and its `## Verification` greps that file. Add the revise fixture. Its spec
  outcome requires `e2e/revise.txt` and `e2e/revise-notes.txt`, but its only
  task writes `e2e/revise.txt`. Register both in `clone.py` the way the existing
  fixtures are registered, and add `EVALUATOR` and the two keys to
  `scenarios.py`.
- [ ] On each harness, add `test_implement_verifies`. On the loop fixture,
  Implement dispatches `iwe-verifier` once, ticks the task with evidence,
  creates the file, and dispatches no evaluator.
- [ ] On each harness, add `test_implement_revises`. On the revise fixture,
  Implement dispatches `iwe-revision-evaluator` once with a prompt naming the
  plan. The plan gains a task in a commit, and both files exist. On Codex, every
  spawn forwards no turns.
- [ ] In each harness's `test_implement`, which uses the greet fixture whose
  task conflicts with the approved text, also assert that no
  `iwe-revision-evaluator` was dispatched.

### Task 6: Run the e2e suite on all three harnesses

**Files:** none

- [ ] Run the implement scenarios live on Claude Code, Codex, and OpenCode
  (`## Verification`), and record the result in `## Verification results`.

### Task 7: Record the design and the changed behavior

**Files:** Create:
`docs/knowledge/data/architecture/autonomous-implement-loop.md`; Modify:
`docs/knowledge/data/architecture.md`,
`docs/knowledge/data/features/verification-in-the-main-loop.md`

- [ ] Write `data/architecture/autonomous-implement-loop.md` with the decisions
  in `## Approach` and their rejected alternatives, linked from
  `data/architecture.md`.
- [ ] In [Verification in the main
  loop](../features/verification-in-the-main-loop.md), replace the Behaviour
  property and the resolved decision that Implement does not invoke Verify. The
  replacement says the Implement orchestrator dispatches `iwe-verifier` after
  the tasks, and Ship stays the mandatory gate before any shipping state change.

### Task 8: Refresh the codebase map

**Files:** Modify: `docs/knowledge/data/codebase/agents/plugins/agentdev.md`,
`docs/knowledge/data/codebase/agents/plugins/agentdev/skills.md`, and any other
doc the map skill reports stale

- [ ] Run `/agentdev:iwe-map` refresh mode so the agent list names `iwe-planner`
  and `iwe-revision-evaluator`, and the skill descriptions match the thin
  `iwe-plan` and the loop.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — scenario sets change and
two requirements are added, so a delta:

``` markdown
## MODIFIED Requirements

### Requirement: Implement never hides a material deviation

The Implement skill SHALL distinguish intent-preserving task corrections from
material changes, SHALL never narrow or extend specified behavior without
either the user's direction or an evaluator-approved plan revision, SHALL leave
to the user every change that drops, narrows, defers, or accepts an exception to
specified behavior, changes `release`, or changes text the user approved, and
SHALL mark a task complete only when its full specified behavior has passing
evidence.

#### Scenario: A tactical correction preserves intent

- **WHEN** implementation reveals a stale anchor or task breakdown that can be
  corrected without changing scope, observable behavior, compatibility,
  acceptance criteria, or dependencies
- **THEN** Implement updates the plan, reports the correction, and may continue
  within the user's requested task boundary

#### Scenario: Completing a task requires extending the plan

- **WHEN** implementation would need an added task or requirement, a heavier
  `## Spec changes` form, or a corrected verification step, keeping every
  specified behavior
- **THEN** Implement leaves the task unchecked and takes the plan through an
  evaluated revision before coding past it

#### Scenario: Completing a task requires narrowing what was agreed

- **WHEN** implementation would need to drop, narrow, defer, or accept an
  exception to specified behavior, change `release`, or change text the user
  approved
- **THEN** Implement leaves the task unchecked, explains the material deviation,
  and waits for user direction before coding past it

#### Scenario: Work is partial or its evidence fails

- **WHEN** a task is only partially implemented, contains deferred behavior, or
  its required tests or checks do not pass
- **THEN** Implement leaves the task unchecked and reports the remaining work or
  failing evidence

### Requirement: Ship and Implement start only from an explicit request or a named dispatcher

The Ship and Implement workflows SHALL each be defined once, as the catalog
agents `iwe-shipper` and `iwe-implementer`. Their user entry skills and the
`iwe-ship-all` and `iwe-implement-all` coordinators SHALL be explicit-only on
Claude Code, Codex, and OpenCode. Only those skills, those coordinators, and
Plan revise mode answering a Ship blocker report SHALL start the workflows. Ship
SHALL always run as a dispatched `iwe-shipper` whose prompt carries only the
plan key, the operation, and the user's approvals quoted verbatim, so its
verification rests on the code and the graph alone. Implement started by the
user's own invocation SHALL run in the user's session. A dispatched workflow
SHALL stop and report at any point that needs a user decision it was not given.

#### Scenario: The user ships a plan directly

- **WHEN** the user runs `/agentdev:iwe-ship <plan>` with no approval
- **THEN** the skill dispatches `iwe-shipper` with the plan key and the ship
  operation and nothing else from the conversation, and the Shipper stops before
  a command with effects beyond the working tree and reports the approval it
  needs.

#### Scenario: The user ships a plan with an approval

- **WHEN** the user re-runs `/agentdev:iwe-ship <plan>` granting the approval
  the Shipper reported
- **THEN** the dispatch prompt quotes that approval verbatim, and the Shipper
  runs the approved command.

#### Scenario: The user implements a plan directly

- **WHEN** the user runs `/agentdev:iwe-implement <plan>` and a task needs a
  material deviation that narrows what was agreed
- **THEN** the session follows the `iwe-implementer` rulebook and waits for the
  user's direction.

#### Scenario: A coordinator ships every implemented plan

- **WHEN** the user runs `/agentdev:iwe-ship-all`
- **THEN** it dispatches one `iwe-shipper` agent per implemented plan in
  dependency order and re-posts each one's Verify verdict and outcome.

#### Scenario: A dispatched workflow reaches a user decision

- **WHEN** a dispatched `iwe-shipper` or `iwe-implementer` reaches a point that
  needs the user
- **THEN** it stops without taking that step and reports what it needs.

#### Scenario: Explore hears a partial answer to an open question

- **WHEN** during `/agentdev:iwe-explore` the user answers an open question in a
  way that leaves a plan apparently complete
- **THEN** Explore neither dispatches `iwe-shipper` nor loads a Ship or
  Implement skill or coordinator, and names the next step for the user.

#### Scenario: A revision answers a Ship blocker

- **WHEN** `/agentdev:iwe-plan` revise mode changes a plan to answer the Ship
  blocker report Ship returned for it, and validation passes
- **THEN** Plan dispatches `iwe-shipper` on that plan, whose Verify decides
  whether it ships.

#### Scenario: The model tries to start a gated skill

- **WHEN** a model on Claude Code, Codex, or OpenCode tries to load `iwe-ship`,
  `iwe-implement`, or either coordinator without a user request
- **THEN** the harness withholds it.

## ADDED Requirements

### Requirement: Implement verifies its own work and acts on the report

When a plan's last task closes, the Implement orchestrator — the user's session
for `/agentdev:iwe-implement`, and the `iwe-implement-all` coordinator for each
plan it runs — SHALL dispatch `iwe-verifier` and SHALL act on every CRITICAL
finding and every WARNING that names a concrete route, reporting SUGGESTIONs
only. A code or evidence finding SHALL be fixed under the Implement rules and
verified again, and a finding about the plan's intent SHALL go through an
evaluated revision. The orchestrator SHALL stop when a finding recurs after a
fix attempt, after three Verify rounds, or after one approved revision in the
run. No agent the loop dispatches SHALL dispatch another.

#### Scenario: Verify finds nothing to act on

- **WHEN** the plan's tasks are closed and `iwe-verifier` reports zero CRITICAL
  findings and no WARNING with a concrete route
- **THEN** the run ends with its rollup and the Verify verdict, and suggests
  `/agentdev:iwe-ship`

#### Scenario: Verify finds a code defect

- **WHEN** the Verify report carries a CRITICAL whose route is code or evidence
- **THEN** the orchestrator fixes it under the Implement rules, closes it with
  evidence, and dispatches `iwe-verifier` again

#### Scenario: A finding recurs

- **WHEN** a finding the orchestrator already tried to fix appears in the next
  Verify report
- **THEN** the run stops and reports the finding, the fix it attempted, and the
  Verify report

#### Scenario: Verify needs an approval

- **WHEN** `iwe-verifier` reports `Needs decision` for a command with effects
  beyond the working tree
- **THEN** the run stops and names the approval, which the user grants by
  re-running the skill

#### Scenario: The coordinator implements every active plan

- **WHEN** the user runs `/agentdev:iwe-implement-all`
- **THEN** the coordinator dispatches `iwe-implementer` once per plan in
  dependency order, runs the same loop for that plan before the next, and
  re-posts each rollup with its Verify and evaluator verdicts

### Requirement: Implement revises its plan only after an independent evaluation

The Plan rulebook SHALL be defined once, as the catalog agent `iwe-planner`,
which `/agentdev:iwe-plan` follows in place. The Implement orchestrator SHALL
revise a plan only by drafting the revision under the `iwe-planner` revise
rules, including its fresh-context audit and validation, leaving it
uncommitted, and dispatching `iwe-revision-evaluator` with a prompt carrying
only the plan key and the finding the revision answers, quoted as reported. It
SHALL commit the revision only on the evaluator's `APPROVE`. On `REJECT` or
`ESCALATE` it SHALL restore the plan from `HEAD` and stop with a report. The
evaluator SHALL judge the uncommitted diff against the plan at `HEAD` and SHALL
never approve a revision that drops, narrows, defers, or accepts an exception to
specified behavior, changes `release`, or changes text the user approved.

#### Scenario: The evaluator approves an added task

- **WHEN** Verify reports a requirement with no implementation, the drafted
  revision adds a task that covers it, and the evaluator returns `APPROVE`
- **THEN** the revision commits, Implement executes the new task, and
  `iwe-verifier` runs again

#### Scenario: The evaluator escalates a narrowing

- **WHEN** a drafted revision would narrow specified behavior
- **THEN** the evaluator returns `ESCALATE`, the orchestrator restores the plan
  from `HEAD`, and the run stops for the user's direction

#### Scenario: The evaluator rejects a restatement

- **WHEN** a drafted revision rewrites the plan's intent to describe the code
  without answering the quoted finding
- **THEN** the evaluator returns `REJECT`, the orchestrator restores the plan
  from `HEAD`, and the run stops with the evaluator's reasons

#### Scenario: The evaluator sees no conversation

- **WHEN** the orchestrator dispatches `iwe-revision-evaluator`
- **THEN** the prompt holds the plan key and the quoted finding and nothing
  else from the conversation, and on Codex the spawn forwards no turns
```

## Depends on

[Run Verify from a fresh context](20261026-verify-in-fresh-context.md) — it
creates `iwe-verifier`, which this plan dispatches.

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
- `uv run pytest .agents/plugins/agentdev/tests`
- `CODEX_HOME=./.tmp/codex-home uv run .agents/plugins/agentdev/bin/install-codex-agents.py`
  writes `agentdev-iwe-planner.toml` with `sandbox_mode = "workspace-write"` and
  `agentdev-iwe-revision-evaluator.toml` with `sandbox_mode = "read-only"`.
- `E2E_RUN_LIVE=1 uv run pytest scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py -k implement`,
  and the same for `test_iwe_workflows_codex.py` and
  `test_iwe_workflows_opencode.py` — each spends model usage.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- A live e2e run of `/agentdev:iwe-implement-all`: it implements every active
  fixture plan in one run. The coordinator's loop is checked by Verify's
  requirement tracing against its skill text.
- Measuring how often the evaluator approves a revision a human would reject.
- Nested dispatch from any catalog agent.
- Ship, Ship-all, and Explore, whose behavior this plan leaves unchanged.

## Key references

Verified anchor points (line numbers as of 2026-10-26):

- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:15` —
  `## How you run`, the two modes
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:74` — step 7,
  classify deviations
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:84` — the material
  deviation branch
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:101` — step 9,
  Finish, which suggests `/agentdev:iwe-verify`
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:142` — `## Rules`
- `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md:13` — the in-place
  follow of the implementer rulebook
- `.agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md:12` — the per-plan
  `iwe-implementer` dispatch
- `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md:19` — `## Steps`, the
  rulebook that moves
- `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md:125` — step 7, the Durable
  Knowledge Auditor gate
- `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md:155` —
  `## Closing the issue`
- `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md:212` — `## Rules`
- `scripts/e2e/iwe-workflows/clone.py:23` — `FIXTURE_PLANS`
- `scripts/e2e/iwe-workflows/clone.py:148` — fixture plans copied into the clone
- `scripts/e2e/iwe-workflows/scenarios.py:8` — `GREET_KEY`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py:99` — `test_implement`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_codex.py:130` — `test_implement`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py:103` —
  `test_implement`
- `docs/knowledge/data/spec/iwe-workflow-skills.md:249` — "Implement never hides
  a material deviation"
- `docs/knowledge/data/spec/iwe-workflow-skills.md:400` — "Ship and Implement
  start only from an explicit request or a named dispatcher"
- `docs/knowledge/data/features/verification-in-the-main-loop.md:50` — the
  Behaviour property that Implement does not invoke Verify
- `docs/knowledge/data/features/verification-in-the-main-loop.md:88` — the
  matching resolved decision
