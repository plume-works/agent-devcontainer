---
type: plan
created: 2026-11-02
release:
- features/agentdev-iwe-workflow-skills
description: Narrow what the Implement loop acts on so it converges — Verify judges conformance only, CI is left to the merge gate, post-merge observations wait for Ship, only CRITICALs create work, and a revision answers its finding without adding promises.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-revision-evaluator.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
stage: done
completed: 2026-11-03
---

# Make the Implement loop converge

## Context

The [Autonomous Implement
loop](../../2.0.0/architecture/autonomous-implement-loop.md) runs Verify, acts
on its findings, and revises the plan through an evaluator. The loop reaches its
three-round stop bound instead of converging. The causes:

- **Evidence timing.** A "CI passes" task, or a task citing a CI run, cannot be
  closed before the pull request exists, and every fix commit makes the cited
  run stale. Post-merge observations (for example "the next Renovate pull
  request receives the bot approval") cannot be closed before merge at all.
- **Warnings become work.** The loop acts on every WARNING whose recommendation
  names a concrete route, and the verifier rulebook requires a concrete
  recommendation on every finding.
- **Verify is not bound to the plan's contract.** A finding need not cite a
  requirement, scenario, task, or verification step, so each fresh round can
  report a weakness no plan claim addresses.
- **Revisions are not bounded to their finding.** `REJECT` covers a revision
  that fails to answer the finding, but not a hunk that answers none or a
  sharpened claim.
- **Repository-wide searches.** A search in `## Verification` reads other plans'
  files, so it fails on text the plan did not change.
- **Content tests.** `AGENTS.md` `### Tests` forbids tests that read files
  instead of running behaviour, and the planner and verifier rulebooks do not
  yet apply that rule to coverage.

The maintainer decided: Verify is a conformance check; "CI passes" is not a plan
task, because `pr-merge` already gates every merge on CI; post-merge
observations stay tasks that Ship waits for; only CRITICALs create work; a
revision adds no promise and changes only lines that answer a finding. The
released behaviour this changes is in [IWE workflow skills in the agentdev
catalog](../../1.0.0/features/agentdev-iwe-workflow-skills.md).

## Approach

Each decision lands in the rulebook that owns it. The planner stops writing CI
tasks and repository-wide searches, marks post-merge observations with a
`**Closed by:**` line, and adopts the approved test-coverage wording. Before
validation it checks each changed requirement against the plan's `## Approach`
and the code it describes, keeps `## Verification` to commands the verifier can
run, and writes requirements that claim only what their mechanism delivers. The
verifier reports only against the plan's contract, lists unticked observation
tasks as outstanding instead of CRITICAL, accepts a CI job as evidence without
requiring a run on the current head, and adopts its approved sentence. The
Implement loop acts on CRITICALs, fixes a WARNING only inside an existing task,
and files the rest through `/agentdev:iwe-capture`. The evaluator rejects a
stray hunk and a new or sharpened claim. Ship refuses while an observation task
is unticked.

Verify stays caller-independent, because the Implement loop and Ship share its
saved report; Ship, not Verify, enforces the observation gate.

Rejected:

- **Verify treats an observation as CRITICAL only when Ship calls it.** The
  saved report would differ by caller, and Ship reuses the loop's report.
- **Delta-scoped Verify rounds.** They treat the symptom; this plan removes its
  causes, CI timing and unbounded probing, at the source.

## Implementation Steps

### Task 1: The planner leaves CI to the merge gate and marks observations

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`

- [x] `## Rules` says a plan carries no task or `## Verification` step whose
  only claim is that CI passes: `pr-merge` gates every merge on CI.

  - **Evidence:** commit c03d084c adds the rule to `iwe-planner.agent.md`
    `## Rules`;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes at 267b16dc.

- [x] `## Rules` says behaviour observable only after merge is a task carrying a
  `**Closed by:** <who or what event>` line, and that Ship waits for it.

  - **Evidence:** commit c03d084c adds the rule to `iwe-planner.agent.md`
    `## Rules`;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes at 267b16dc.

- [x] `## Rules` carries this approved paragraph verbatim:

  ``` text
  A scenario is covered by a test only when the test runs the behaviour: it executes the code, script, hook, or command under test with inputs it controls, owns every resource it uses, and checks what results. These do not cover behaviour: a test that reads a repository file to check its text, keys, steps, or versions, or that two files agree; a test that checks another tool did its job; and a test that queries a live service or waits on CI. Behaviour no such test can reach is an observation task that names who closes it, and Ship waits for it.
  ```

  - **Evidence:** commit c03d084c adds the paragraph to `iwe-planner.agent.md`
    `## Rules` byte for byte;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes at 267b16dc.

- [x] Step 4's `## Verification` bullet says a search for leftover text covers
  only the files the plan changes.

  - **Evidence:** commit c03d084c adds the sentence to `iwe-planner.agent.md`
    step 4's `## Verification` bullet;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes at 267b16dc.

- [x] `## Rules` says that before validation the planner checks each requirement
  in `## Spec changes` that the plan adds or modifies against the plan's
  `## Approach` and against the code it describes, and resolves every
  disagreement in the plan before it is written.

  - **Evidence:** commit c03d084c adds the rule to `iwe-planner.agent.md`
    `## Rules`;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes at 267b16dc.

- [x] Step 4's `## Verification` bullet says each command runs in the checkout
  the `iwe-verifier` agent works in — inside the Dev Container or container the
  agent already runs in — without starting a nested Dev Container and without
  CI; a check that needs either is a cited CI job or a task carrying a
  `**Closed by:**` line.

  - **Evidence:** commit c03d084c adds the sentence to `iwe-planner.agent.md`
    step 4's `## Verification` bullet;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes at 267b16dc.

- [x] `## Rules` says a requirement in `## Spec changes` claims only what its
  mechanism delivers and names each limit of that mechanism the planner knows.

  - **Evidence:** commit c03d084c adds the rule to `iwe-planner.agent.md`
    `## Rules`;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes at 267b16dc.

### Task 2: Verify judges conformance to the plan

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-verifier.agent.md`

- [x] Step 3 says every CRITICAL and WARNING cites the requirement, scenario,
  task, or verification step of the effective contract it contradicts; a
  weakness the contract does not address is not reported as either.

  - **Evidence:** commit c03d084c adds the citation rule to
    `iwe-verifier.agent.md` step 3;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes at 267b16dc.

- [x] Completeness lists an unticked task carrying a `**Closed by:**` line under
  a new **Outstanding observations** report heading instead of as a CRITICAL.

  - **Evidence:** commit c03d084c changes Completeness in
    `iwe-verifier.agent.md` to list the task under **Outstanding observations**;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes at 267b16dc.

- [x] Completeness accepts a CI job as evidence for behaviour only CI exercises
  when the job exercises it, without requiring a run on the current head.

  - **Evidence:** commit c03d084c adds the CI-job sentence to Completeness in
    `iwe-verifier.agent.md`;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes at 267b16dc.

- [x] Correctness judges coverage by the `iwe-planner` coverage rule (Task 1),
  and replaces "(uncovered scenario is a WARNING)" with this approved sentence
  verbatim:

  ``` text
  An uncovered scenario is a WARNING only when a test of that kind could cover it; a check of file contents never counts as coverage.
  ```

  - **Evidence:** commit c03d084c applies the `iwe-planner` coverage rule in
    `iwe-verifier.agent.md` Correctness and adds the approved sentence byte for
    byte;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes at 267b16dc.

- [x] `## Report` lists **Outstanding observations** after the findings.

  - **Evidence:** commit c03d084c adds the heading to `iwe-verifier.agent.md`
    `## Report` after the findings;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes at 267b16dc.

### Task 3: The Implement loop acts on CRITICALs and files the rest

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-implementer.agent.md`

- [x] `## Running the loop` step 2 acts on every CRITICAL, and on a WARNING only
  when its fix fits a task the plan already has and adds no claim the code must
  newly meet; every other WARNING is filed through `/agentdev:iwe-capture` and
  named in the report. Outstanding observations do not stop the run; the report
  names them.
  - **Evidence:** commit c03d084c rewrites step 2 of `## Running the loop` in
    `iwe-implementer.agent.md`;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes at 267b16dc.
- [x] Step 4's drafting sub-step says the revision changes only lines that
  answer the quoted finding and adds or sharpens no claim the code must newly
  meet.
  - **Evidence:** commit c03d084c adds the sentence to step 4's drafting
    sub-step in `iwe-implementer.agent.md`;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes at 267b16dc.

### Task 4: The evaluator rejects stray hunks and new promises

**Files:** Modify:
`.agents/plugins/agentdev/agents/iwe-revision-evaluator.agent.md`

- [x] `REJECT` gains two conditions: a hunk that answers no quoted finding, and
  a hunk that adds or sharpens a claim the code must newly meet.
  - **Evidence:** commit c03d084c adds both bullets to `REJECT` in
    `iwe-revision-evaluator.agent.md`;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes at 267b16dc.
- [x] `APPROVE` lists "an added task toward a requirement the plan already
  states" in place of "an added task or requirement", and allows a heavier
  `## Spec changes` form only when it states no claim beyond the lighter one.
  - **Evidence:** commit c03d084c rewrites both `APPROVE` bullets in
    `iwe-revision-evaluator.agent.md`;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes at 267b16dc.

### Task 5: Ship waits for post-merge observations

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-shipper.agent.md`

- [x] Normal shipping stops with a Ship blocker report while any task carrying a
  `**Closed by:**` line is unticked, before any shipping state transition.
  - **Evidence:** commit c03d084c adds the gate to step 3 and `## Rules` in
    `iwe-shipper.agent.md`;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes at 267b16dc.
- [x] The blocker report's routes add: observe it, tick it with evidence, then
  run `/agentdev:iwe-ship` again.
  - **Evidence:** commit c03d084c adds the **Outstanding observation** route to
    the Ship blocker report in `iwe-shipper.agent.md`;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes at 267b16dc.

### Task 6: Record the decisions

**Files:** Modify:
`docs/knowledge/data/archive/2.0.0/architecture/autonomous-implement-loop.md`

- [x] The decision states what the loop acts on (CRITICALs; a WARNING only
  inside an existing task), that Verify is a conformance check, that CI belongs
  to `pr-merge` and post-merge observations to Ship, and the evaluator's two new
  `REJECT` conditions.
  - **Evidence:** commit c03d084c adds the paragraph "The loop acts only on what
    the plan promised" and both `REJECT` bullets to
    `autonomous-implement-loop.md` `## Decision`; `iwe schema validate` passes
    at 267b16dc.
- [x] `## Rejected alternatives` adds the two alternatives in `## Approach`.
  - **Evidence:** commit c03d084c adds both alternatives to
    `autonomous-implement-loop.md` `## Rejected alternatives`;
    `iwe schema validate` passes at 267b16dc.

## Spec changes

[IWE workflow skills](../../../spec/iwe-workflow-skills.md) — two Implement
requirements change, and three requirements are added for Verify, Ship, and
Plan.

``` markdown
## MODIFIED Requirements

### Requirement: Implement verifies its own work and acts on the report

When a plan's last task closes, the Implement orchestrator — the user's session
for `/agentdev:iwe-implement`, and the `iwe-implement-all` coordinator for each
plan it runs — SHALL run Verify through `/agentdev:iwe-verify` and SHALL act on
every CRITICAL finding, and on a WARNING only when its fix fits a task the plan
already has and adds no claim the code must newly meet. It SHALL file every
other WARNING through `/agentdev:iwe-capture`, report SUGGESTIONs only, and
SHALL not stop for an outstanding observation. A code or evidence finding SHALL
be fixed under the Implement rules and verified again, and a finding about the
plan's intent SHALL go through an evaluated revision. The orchestrator SHALL
stop when a finding recurs after a fix attempt, after three Verify rounds, or
after one approved revision in the run. No agent the loop dispatches SHALL
dispatch another.

#### Scenario: Verify finds nothing to act on

- **WHEN** the plan's tasks are closed and Verify reports zero CRITICAL findings
  and no WARNING whose fix fits an existing task
- **THEN** the run ends with its rollup and the Verify verdict, and suggests
  `/agentdev:iwe-ship`

#### Scenario: Verify finds a code defect

- **WHEN** the Verify report carries a CRITICAL whose route is code or evidence
- **THEN** the orchestrator fixes it under the Implement rules, closes it with
  evidence, and runs Verify again through `/agentdev:iwe-verify`

#### Scenario: A warning would add work

- **WHEN** Verify reports a WARNING whose fix needs a new task or a new claim
- **THEN** the orchestrator files it through `/agentdev:iwe-capture`, names it
  in the report, and does not act on it in this run

#### Scenario: An observation is outstanding

- **WHEN** Verify lists an unticked `**Closed by:**` task under Outstanding
  observations and reports nothing else to act on
- **THEN** the run ends with its rollup naming the observation

#### Scenario: A finding recurs

- **WHEN** a finding the orchestrator already tried to fix appears in the next
  Verify report
- **THEN** the run stops and reports the finding, the fix it attempted, and the
  Verify report

#### Scenario: Verify needs an approval

- **WHEN** Verify reports `Needs decision` for a command with effects beyond the
  working tree
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
rules, including its fresh-context audit and validation, changing only lines
that answer the quoted finding, leaving it uncommitted, and dispatching
`iwe-revision-evaluator` with a prompt carrying only the plan key and the
finding the revision answers, quoted as reported. It SHALL commit the revision
only on the evaluator's `APPROVE`. On `REJECT` or `ESCALATE` it SHALL restore
the plan from `HEAD` and stop with a report. The evaluator SHALL judge the
uncommitted diff against the plan at `HEAD`, SHALL never approve a revision
that drops, narrows, defers, or accepts an exception to specified behavior,
changes `release`, or changes text the user approved, and SHALL reject a
revision with a hunk that answers no quoted finding or that adds or sharpens a
claim the code must newly meet.

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

#### Scenario: The evaluator rejects a stray hunk

- **WHEN** a drafted revision answers the quoted finding and also changes lines
  the finding does not concern
- **THEN** the evaluator returns `REJECT` naming the stray hunk

#### Scenario: The evaluator rejects a sharpened promise

- **WHEN** a drafted revision rewrites a requirement into a stricter claim the
  code must newly meet
- **THEN** the evaluator returns `REJECT`

#### Scenario: The evaluator sees no conversation

- **WHEN** the orchestrator dispatches `iwe-revision-evaluator`
- **THEN** the prompt holds the plan key and the quoted finding and nothing else
  from the conversation

## ADDED Requirements

### Requirement: Verify judges conformance to the plan

Verify SHALL report a CRITICAL or WARNING finding only against a requirement,
scenario, task, or verification step of the plan's effective contract, citing
it. It SHALL treat a scenario as uncovered only when a test that runs the
behaviour could cover it, and SHALL never count a check of file contents as
coverage. It SHALL accept a CI job as evidence for behaviour only CI exercises
when the job exercises that behaviour, without requiring a run on the current
head. It SHALL list an unticked task carrying a `**Closed by:**` line under
Outstanding observations rather than as a CRITICAL.

#### Scenario: A weakness the plan does not address

- **WHEN** Verify notices a way to defeat the code that no requirement,
  scenario, task, or verification step of the plan addresses
- **THEN** it reports no CRITICAL or WARNING for it

#### Scenario: A scenario has only a content test

- **WHEN** the only test for a scenario reads a repository file to check its
  text
- **THEN** Verify counts the scenario as uncovered only if a test that runs the
  behaviour could cover it, and never counts the content test as coverage

#### Scenario: A post-merge observation is unticked

- **WHEN** the plan's only unticked task carries a `**Closed by:**` line
- **THEN** Verify lists it under Outstanding observations and reports no
  CRITICAL for it

#### Scenario: A CI job ran on an earlier commit

- **WHEN** a task cites a CI job that exercises behaviour only CI reaches, and
  the run cited is on an earlier commit than `HEAD`
- **THEN** Verify accepts the evidence

### Requirement: Ship waits for post-merge observations

Ship SHALL refuse normal shipping while the plan has an unticked task carrying a
`**Closed by:**` line, SHALL make no shipping state transition, and SHALL name
each such task in its blocker report with the route: observe it, tick it with
evidence, then run Ship again.

#### Scenario: An observation is still open

- **WHEN** Ship runs on a plan whose Verify report has no CRITICAL and lists an
  outstanding observation
- **THEN** the Shipper returns `Blocked` naming the observation and changes no
  state

### Requirement: Plans test behaviour and leave CI to the merge gate

Plan SHALL write no task or verification step whose only claim is that CI
passes, SHALL record behaviour observable only after merge as a task carrying a
`**Closed by:**` line, SHALL name a test as coverage only when it runs the
behaviour, and SHALL scope a verification search for leftover text to the files
the plan changes. Before validation, Plan SHALL check each requirement it adds
or modifies against the plan's `## Approach` and the code that requirement
describes. Every `## Verification` command SHALL run in the checkout the
`iwe-verifier` agent works in, inside the Dev Container or container the agent
already runs in, without starting a nested Dev Container or CI. A
requirement SHALL claim only what its mechanism delivers and name each limit of
that mechanism Plan knows.

#### Scenario: A plan's work needs CI

- **WHEN** Plan writes a plan whose change is checked by CI
- **THEN** the plan carries no "CI passes" task or verification step

#### Scenario: Behaviour is visible only after merge

- **WHEN** a requirement can be observed only once the change is on the default
  branch
- **THEN** Plan writes a task for it carrying a `**Closed by:**` line naming who
  or what closes it

#### Scenario: A requirement disagrees with the code

- **WHEN** a requirement Plan adds or modifies states a restriction the code it
  describes does not hold, or contradicts the plan's `## Approach`
- **THEN** Plan changes the requirement, the `## Approach`, or adds a task
  before validation, and the plan carries no disagreement

#### Scenario: A check needs a nested Dev Container

- **WHEN** proving the work needs a command that runs only after starting a
  nested Dev Container
- **THEN** `## Verification` does not list the command; the plan cites a CI job
  that runs it or adds a task carrying a `**Closed by:**` line

#### Scenario: A mechanism has a known limit

- **WHEN** Plan writes a requirement for a mechanism with a limit it knows of
- **THEN** the requirement names that limit
```

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude`
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- e2e scenarios for the changed rulebooks.
- Removing existing content tests — [Remove tests that check file contents
  instead of running behaviour](../backlog/remove-content-tests.md).
- The adversarial review agent ([Add an adversarial review for plans and their
  code](20261102-adversarial-review.md)) and Ship's user-only guard ([Let any
  session asked to ship a named plan start
  Ship](../../3.0.0/plans/20261102-model-invocable-ship.md)).
- The stop bounds, always-escalate deviations, and `Needs decision` — unchanged.
- Rewriting existing plans' "CI passes" tasks.

## Key references

- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps › "## Implementation Steps"`
  — `## Implementation Steps` bullet
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps › "— how a session proves the work is done: commands"`
  — `## Verification` bullet
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#rules` — `## Rules`
- `.agents/plugins/agentdev/agents/iwe-verifier.agent.md#steps › "task carrying a"`
  — Completeness
- `.agents/plugins/agentdev/agents/iwe-verifier.agent.md#steps › "An uncovered scenario is a WARNING only when a test of that"`
  — uncovered-scenario sentence
- `.agents/plugins/agentdev/agents/iwe-verifier.agent.md#report` — `## Report`
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#running-the-loop › "every CRITICAL, and a WARNING only when its"`
  — loop step 2, findings to act on
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#running-the-loop › "— a finding about the plan's intent, such as a"`
  — loop step 4, revision route
- `.agents/plugins/agentdev/agents/iwe-revision-evaluator.agent.md#rubric › "— the revision may not land as drafted. Any revision that"`
  — `REJECT`
- `.agents/plugins/agentdev/agents/iwe-revision-evaluator.agent.md#rubric › "— everything else, provided every specified behavior"`
  — `APPROVE`
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps › "Run Verify for normal shipping."`
  — step 3, Verify for normal shipping
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#report › "names the plan, and lists every"`
  — Ship blocker report
- `docs/knowledge/data/archive/2.0.0/architecture/autonomous-implement-loop.md#decision`
  — `## Decision`
- `docs/knowledge/data/archive/2.0.0/architecture/autonomous-implement-loop.md#rejected-alternatives`
  — `## Rejected alternatives`
- `docs/knowledge/data/spec/iwe-workflow-skills.md#scenario-implementation-starts-on-a-feature-branch › "Implement begins with a branch other than"`
  — Implement verifies requirement
- `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-implement-verifies-its-own-work-and-acts-on-the-report`
  — Implement revises requirement
- `docs/knowledge/data/spec/iwe-workflow-skills.md#scenario-the-evaluator-approves-an-added-task › "revision adds a task that covers it, and the evaluator"`
  — Normal shipping requirement
