---
type: plan
stage: done
completed: 2026-11-03
created: 2026-10-31
release:
- features/agentdev-iwe-workflow-skills
description: Drop the explicit-only gate on the iwe-implement skill so any session asked to implement a named plan — including one a coordinator asks — can load it, take decisions from its own user or from approvals a coordinator relays from the user, and have Plan and Explore neither start Implement nor name it as a next step.
sources:
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-explore/SKILL.md
- resource: docs/knowledge/data/archive/2.0.0/architecture/explicit-only-workflow-agents.md
released: 2.1.0
---

# Let any session asked to implement a named plan start Implement

## Context

The agentdev workflow lays plans out first and has a coordinator work through
them. A coordinator running `/agentdev:iwe-implement-all` hands plans to
long-running peer sessions over cross-session messages, and each of those
sessions is refused when it loads `/agentdev:iwe-implement`: the skill carries
`disable-model-invocation: true`, and its text forbids dispatching
`iwe-implementer` as a subagent. Every plan therefore waits for the user to type
the command in that session.

The gate exists so that a description match cannot start a workflow — see
[Explicit-only workflow
agents](../archive/2.0.0/architecture/explicit-only-workflow-agents.md). The
maintainer decided that Implement no longer needs it: implementing directly from
a just-written plan is reserved for small isolated changes, so Plan and Explore
can drop Implement as a suggested next step, and those two were the sessions
where an unintended start could happen. Ship keeps its gate: a stray Ship run
reaches the remote.

The released behavior this changes is in [IWE workflow skills in the agentdev
catalog](../archive/1.0.0/features/agentdev-iwe-workflow-skills.md).

## Approach

This lands after [Remove Codex support](20261031-remove-codex.md), so the gate
is the `disable-model-invocation` key alone: Claude Code reads it, and the
OpenCode bridge turns it into a skill `deny`. It also lands after [Explore
proposes only for observed problems](20261103-explore-evidence-gate.md); the
Explore requirement delta below keeps that plan's text. Remove the key from
`iwe-implement`. Narrow its description to a request that names a plan, so an
ordinary "implement this fix" does not load it. `iwe-implement-all`, `iwe-ship`,
and `iwe-ship-all` stay explicit-only.

A session that loads Implement on another session's message follows the rulebook
in place, like a direct run. The plan comes from the request. A decision the
rulebook asks for comes from that session's own user, or from an approval of the
user's that a coordinator session relays: the coordinator asks the user its
questions in one place and passes the answers to the sessions it runs.

Plan and Explore neither load Implement nor name it as a next step. Plan's
readiness report ends at readiness; Explore hands a finding back to Plan. Ship's
blocker report keeps naming Implement, since it follows a plan that already ran.

Rejected:

- **A separate model-invocable entry skill that runs only on a coordinator's
  request.** Its description is still listed to the model, and the "only on a
  coordinator request" check is a prompt-level self-check — the alternative the
  architecture document already rejects.
- **Workers following the rulebook file without the skill.** A worker that tried
  the gated skill first sees the refusal text, which tells it not to replicate
  the workflow by other means, so the route depends on the coordinator never
  mentioning the skill.

## Implementation Steps

### Task 1: Remove the gate from iwe-implement

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md`

- [x] `SKILL.md` carries no `disable-model-invocation` key.
  - **Evidence:** commit a964f0be drops the key from the frontmatter;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    reports 61/61 skills valid at that commit.
- [x] The description says the skill is for a request that names a plan to
  implement, so a request with no plan does not match it.
  - **Evidence:** commit a964f0be — the description reads "Use only when the
    request names the plan to implement; a request to build something with no
    plan named does not match."
- [x] The body follows the rulebook "for the plan the request names" instead of
  "the plan the user named", and keeps its rule that only
  `/agentdev:iwe-implement-all` dispatches `iwe-implementer`.
  - **Evidence:** commit a964f0be — the body reads "for the plan the request
    names" and keeps "Do not dispatch it as a subagent: only
    `/agentdev:iwe-implement-all` does that."
- [x] `bun test ./.agents/plugins/agentdev/tests/opencode/bridge.test.ts`
  passes.
  - **Evidence:** at commit a964f0be,
    `bun test ./.agents/plugins/agentdev/tests/opencode/bridge.test.ts` (bun
    1.4.4 needs the `./` to read the argument as a path) — 29 pass, 0 fail.

### Task 2: Take decisions from the user, directly or relayed

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-implementer.agent.md`

- [x] The **In the user's session** mode covers a session that loaded
  `/agentdev:iwe-implement` on the user's command, on a plain request, or on a
  message from another session such as a coordinator.
  - **Evidence:** commit 8ede183b — the mode opens "the session loaded
    `/agentdev:iwe-implement` on the user's command, on a plain request, or on a
    message from another session such as a coordinator"; the validator reports
    61/61 valid at that commit.
- [x] The mode states that the plan comes from the request, that a decision the
  rulebook asks for is answered by this session's own user or by an approval of
  the user's that a coordinator's message relays, and that while waiting the
  session tells the requesting session what it is waiting on.
  - **Evidence:** commit 8ede183b — the mode reads "The plan comes from the
    request", "answered by this session's own user, or by an approval of the
    user's that a coordinator's message relays", and "tell a requesting session
    what you are waiting on".
- [x] The rollup goes back to the requesting session as well as this one.
  - **Evidence:** commit 8ede183b — the mode ends "Send the rollup back to a
    requesting session as well as reporting it here."

### Task 3: Plan never starts or names Implement

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`

- [x] The opening paragraph and step 8's report say Plan never loads
  `/agentdev:iwe-implement`, never dispatches `iwe-implementer`, and never names
  Implement as a next step; the report ends at readiness.
  - **Evidence:** commit fc486edb adds the rule to the opening paragraph and to
    step 8's report ("The report ends at readiness: it never names Implement as
    a next step"); the validator reports 61/61 valid at that commit.
- [x] The **From the Implement orchestrator** mode is unchanged: the
  orchestrator follows Plan, and Plan never calls back into Implement.
  - **Evidence:** `git show fc486edb` touches only the opening paragraph and
    step 8's report; the mode still stops with the revision uncommitted for
    `iwe-revision-evaluator` and loads no Implement skill.

### Task 4: Explore never names Implement

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md`

- [x] `## During implementation` hands a decision, scope change, or new work to
  `/agentdev:iwe-plan` only, and `## Rules` points only at `/agentdev:iwe-plan`;
  neither names `/agentdev:iwe-implement`.
  - **Evidence:** commit 149e8843; at that commit
    `git grep -n "iwe-implement" .agents/plugins/agentdev/skills/iwe-explore`
    prints nothing, and the validator reports 61/61 valid.
- [x] Explore still never starts Plan or Implement itself.
  - **Evidence:** commit 149e8843 — `## During implementation` reads "never
    start Plan or Implement from Explore or silently change the plan." Commit
    c0533739 rewords `## Rules`' closing next step from "return to
    implementation" to "return to the plan"; at that commit
    `git grep -n "return to implementation" .agents/plugins/agentdev/skills/iwe-explore`
    prints nothing.

### Task 5: e2e scenarios for a requested run and for Plan and Explore

**Files:** Modify: `scripts/e2e/iwe-workflows/scenarios.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py`,
`scripts/e2e/iwe-workflows/harness_opencode.py`,
`scripts/e2e/iwe-workflows/harness_claude.py`

- [x] On Claude Code and OpenCode, a plain prompt asking to implement
  `GREET_KEY`, with no command, loads the `iwe-implement` skill through the
  skill tool and reads `RULEBOOK` in session, with the same tree assertions as
  `test_implement`. The OpenCode harness gains a run that posts a prompt instead
  of a command.
  - **Evidence:** commit 4c03b7d6 adds `test_implement_requested` to both
    suites, sharing `assert_greet_stopped` with `test_implement`, and
    `OpenCodeServer.prompt`, which posts to `/api/session/<id>/prompt`; at that
    commit
    `OPENCODE_BIN=opencode uv run pytest scripts/tests/test_e2e_iwe_workflows_opencode_server.py`
    — 4 passed.
- [x] On Claude Code and OpenCode, `/agentdev:iwe-plan` asked to plan a small
  change "and then build it" loads no `iwe-implement` skill, dispatches no
  `iwe-implementer`, edits nothing outside `docs/knowledge/`, and its final
  message does not name `iwe-implement`.
  - **Evidence:** commit 4c03b7d6 adds `test_plan_does_not_implement` to both
    suites, with `Clone.changed_outside` and the `PLAN_AND_BUILD` request;
    `uv run pytest --collect-only scripts/e2e/iwe-workflows` collects 46 tests
    at that commit.
- [x] `test_explore` on both harnesses also asserts the final message does not
  name `iwe-implement`; the harnesses gain a final-message accessor if they lack
  one.
  - **Evidence:** commit 4c03b7d6 — both `test_explore` functions assert
    `NAMES_IMPLEMENT` does not match `transcript.final_text()`, the accessor
    both harnesses already had.
- [x] `uv run pytest --collect-only scripts/e2e/iwe-workflows` passes.
  - **Evidence:** at commit 4c03b7d6 the command collects 46 tests with no
    error, and `uv run ruff check scripts/e2e/iwe-workflows` passes.

### Task 6: The new and changed e2e scenarios pass

- [x] The Task 5 scenarios and the existing `test_implement` and `test_explore`
  pass on Claude Code and on OpenCode with the default test models.
  - **Evidence:** at commit 5ede7bd0 (code from 4c03b7d6),
    `E2E_RUN_LIVE=1 uv run pytest -n 3 scripts/e2e/iwe-workflows -k "test_implement and not (verifies or revises or all or stops or main) or test_plan_does_not_implement or test_explore"`
    — 8 passed: `test_implement`, `test_implement_requested`,
    `test_plan_does_not_implement`, and `test_explore` on each harness, with the
    default OpenCode models.

### Task 7: Record the decision in the architecture document

**Files:** Modify:
`docs/knowledge/data/archive/2.0.0/architecture/explicit-only-workflow-agents.md`

- [x] **Who may start them** lists any session asked to implement a named plan,
  including on a coordinator's message, for Implement; Ship's callers are
  unchanged.
  - **Evidence:** commit 5b4b924a lists "any session asked to implement a named
    plan — by the user's `/agentdev:iwe-implement`, by a plain request, or by a
    message from a coordinator session"; the Ship callers keep their bullets;
    `iwe schema validate` passes at that commit.
- [x] The gate bullet names only `iwe-ship`, `iwe-ship-all`, and
  `iwe-implement-all` as entry points under the gate, and **Implement keeps the
  user's session** states the authority rule from Task 2, including approvals a
  coordinator relays.
  - **Evidence:** commit 5b4b924a — the gate bullet reads "Of the entry points,
    `iwe-ship`, `iwe-ship-all`, and `iwe-implement-all` carry" the key, and
    **Implement keeps the user's session** adds "A decision the rulebook asks
    for comes from that session's own user, or from an approval of the user's
    that a coordinator session relays in its message".
- [x] The decision states why Implement can drop the gate — it needs a named
  active plan with satisfied dependencies and asks when the plan is ambiguous,
  and Plan and Explore never name it — and **Drop the gate and rely on
  descriptions** stays rejected for Ship, with its Explore example.
  - **Evidence:** commit 5b4b924a adds **Implement's entry skill is
    model-invocable** ("needs a named active plan whose dependencies are done
    and asks when the plan is ambiguous … Plan and Explore … never name it") and
    retitles the rejection **Drop the gate and rely on descriptions, for Ship**,
    keeping its Explore example.
- [x] The two alternatives rejected in `## Approach` are added under
  `## Rejected alternatives`.
  - **Evidence:** commit 5b4b924a adds **A separate model-invocable Implement
    entry skill that runs only on a coordinator's request** and **Workers
    following the rulebook file without the skill** under
    `## Rejected alternatives`.

### Task 8: A coordinator's message names a plan to implement

**Files:** Modify: `scripts/e2e/iwe-workflows/scenarios.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py`

- [x] On Claude Code and OpenCode, a plain message written as a coordinator
  session's, asking to implement `GREET_KEY`, loads the `iwe-implement` skill
  and passes the same assertions as `test_implement_requested`: the rulebook
  read in session, nothing dispatched, and the greet task handled as in
  `test_implement`.
  - **Evidence:** commit 1b8ea659 adds `COORDINATOR_REQUEST` and
    `test_implement_coordinator_requested` to both suites, sharing
    `assert_greet_stopped` with `test_implement_requested`, and removes
    `RELAYED_NARROWING` and `test_implement_relayed_narrowing`; at that commit
    `uv run pytest --collect-only scripts/e2e/iwe-workflows` collects 48 tests
    and the ruff pre-commit hooks pass.
- [x] That scenario passes on Claude Code and on OpenCode with the default test
  models.
  - **Evidence:** at commit 1b8ea659,
    `E2E_RUN_LIVE=1 uv run pytest -n 2 scripts/e2e/iwe-workflows -k test_implement_coordinator_requested`
    — 2 passed: `test_implement_coordinator_requested` on each harness, with the
    default OpenCode models.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — three requirements
change: Implement's entry skill becomes model-invocable, taking decisions from
the session's own user or approvals a coordinator relays from the user, and Plan
and Explore stop naming Implement.

``` markdown
## MODIFIED Requirements

### Requirement: Explore remains an adaptive thinking mode

The Explore skill SHALL investigate the project graph and codebase without
editing application code, SHALL remain adaptive and patient as the problem takes
shape, and SHALL offer capture or a phase handoff without pressuring the user to
formalize unfinished thinking. Explore SHALL neither start Implement nor name it
as a next step. Explore SHALL propose a change only for a problem it can show has
occurred, SHALL list a case it can only imagine as not observed rather than
design for it, and SHALL weigh a risk its own proposal creates against that
proposal rather than open it as a new question. When the user approves specific
text, Explore SHALL persist it verbatim outside the conversation and reproduce it
verbatim in the handoff, and SHALL never paraphrase it. Once the problem has open
questions, Explore SHALL settle them with the user one at a time — one topic per
turn and one decision per question, in the user's names and design — and SHALL
record each answer verbatim as it is given.

#### Scenario: Exploration starts from an open-ended idea

- **WHEN** the user asks to explore an idea without committing to implementation
- **THEN** Explore follows relevant questions and tradeoffs, grounds claims in
  current project evidence, and ends with the current understanding and an
  optional next step

#### Scenario: Exploration starts from a GitHub issue

- **WHEN** the user invokes Explore with an issue URL, an `OWNER/REPO#N`
  reference, or an issue number
- **THEN** Explore reads the issue and all of its comments into `./.tmp/` before
  investigating, verifies the issue's claims against the code and the graph
  rather than adopting them, never edits the issue, and carries the issue URL
  into any handoff to Plan

#### Scenario: Exploration starts during implementation

- **WHEN** the user invokes Explore because an active implementation task
  exposed a complication
- **THEN** Explore reads the active plan and task, investigates without editing
  code, and hands any resulting decision, scope change, or new work to Plan,
  without naming Implement

#### Scenario: The user approves specific wording

- **WHEN** the user agrees to specific text — wording for a document, a snippet,
  a message — that a later plan or edit will apply
- **THEN** Explore writes it verbatim to `.tmp/approved-wording-<slug>.md`
  before continuing, names that file in the handoff, and reproduces the text
  verbatim rather than describing it

#### Scenario: The exploration has open questions

- **WHEN** the problem being explored has more than one open question
- **THEN** Explore names one topic and stays on it until the user settles it,
  asks one decision at a time as numbered options with a recommendation, keeps
  the user's names and design unless changing them is the question asked,
  settles a question about system behavior with evidence before asking it,
  records each answer verbatim in `.tmp/approved-wording-<slug>.md` — marked
  approved only on an explicit yes — and opens the next topic only after the
  current one is settled

#### Scenario: Exploration proposes a change

- **WHEN** Explore is about to propose a change to the system
- **THEN** it first collects and counts the observed occurrences of the problem,
  proposes the smallest change that would have prevented them, lists any case
  it can only imagine under "not observed", and opens no thread or open
  question for a risk that exists only because of its own proposal

### Requirement: Plan creates or revises planning state without implementing

The Plan skill SHALL treat its invocation as authorization to write planning
state only, SHALL resolve material ambiguity before committing the plan, and
SHALL keep a created or revised plan coherent across context, approach, tasks,
spec impact, dependencies, verification, out-of-scope boundaries, and current
code anchors. Plan SHALL neither start Implement nor name it as a next step.
When a decision was made as specific text, Plan SHALL reproduce that text
verbatim in the task that applies it and SHALL never paraphrase it.

#### Scenario: A plan grows from a GitHub issue

- **WHEN** Plan creates a plan for work that arrived as a GitHub issue
- **THEN** the plan links the issue URL in `## Context` and under `sources:`,
  and after the plan validates, Plan closes the issue with a comment naming the
  plan path, so the issue and the plan reference each other and the issue no
  longer competes with the plan as the open record of the work

#### Scenario: A planning request also asks to build the change

- **WHEN** a request invokes Plan while also asking for implementation
- **THEN** Plan creates and validates the planning state, reports readiness
  without naming Implement, and stops before editing implementation code,
  neither loading Implement nor dispatching `iwe-implementer`

#### Scenario: Ambiguity would alter observable behavior

- **WHEN** an unresolved choice would materially affect scope, externally
  observable behavior, compatibility, or acceptance criteria
- **THEN** Plan asks for direction before committing that choice

#### Scenario: Only a minor detail is unspecified

- **WHEN** an unspecified detail does not materially affect scope, behavior,
  compatibility, or acceptance criteria
- **THEN** Plan makes a reasonable assumption and records it in the plan

#### Scenario: An active plan is revised

- **WHEN** the user requests a specific revision to an existing active plan
- **THEN** Plan reconciles every affected section in either direction,
  re-verifies any affected code anchors, validates the graph, and reports
  implementation that may now be stale

#### Scenario: A revision changes the work's intent

- **WHEN** a proposed revision creates a different topic or materially different
  verification story
- **THEN** Plan recommends distinct work instead of silently replacing the
  existing plan's intent

#### Scenario: A task applies text the user already approved

- **WHEN** a plan task would apply wording, a snippet, or a message that the
  user has already agreed to
- **THEN** Plan reproduces that text verbatim in a fenced block under the task,
  consulting `.tmp/approved-wording-<slug>.md` rather than writing it from
  memory, so a session holding only the plan can reproduce the approved bytes

### Requirement: Ship and Implement start only from an explicit request or a named dispatcher

The Ship and Implement workflows SHALL each be defined once, as the catalog
agents `iwe-shipper` and `iwe-implementer`. Ship's user entry skill and the
`iwe-ship-all` and `iwe-implement-all` coordinators SHALL be explicit-only on
Claude Code and OpenCode. Implement's entry skill SHALL be model-invocable on
both, so a session asked to implement a named plan
may load it, including on a message from a coordinator session. Only those
skills, those coordinators, and Plan revise mode answering a Ship blocker report
SHALL start the workflows. Ship SHALL always run as a dispatched `iwe-shipper`
whose prompt carries only the plan key, the operation, and the user's approvals
quoted verbatim, so its verification rests on the code and the graph alone.
Implement started through its entry skill SHALL run in the session that loaded
it and SHALL take every decision from that session's own user or from an
approval of the user's that a coordinator session relays. A dispatched workflow
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

#### Scenario: A session is asked in plain words to implement a plan

- **WHEN** the user asks a session to implement a named plan without typing the
  command
- **THEN** the session loads `/agentdev:iwe-implement` and follows the
  `iwe-implementer` rulebook in place, dispatching no `iwe-implementer`.

#### Scenario: A coordinator asks a session to implement a plan

- **WHEN** a coordinator session sends a session a message asking it to
  implement a named plan
- **THEN** the session loads `/agentdev:iwe-implement` and follows the
  `iwe-implementer` rulebook in place, dispatching no `iwe-implementer`.

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
  Implement skill or coordinator, and names a next step for the user other than
  Implement.

#### Scenario: A revision answers a Ship blocker

- **WHEN** `/agentdev:iwe-plan` revise mode changes a plan to answer the Ship
  blocker report Ship returned for it, and validation passes
- **THEN** Plan dispatches `iwe-shipper` on that plan, whose Verify decides
  whether it ships.

#### Scenario: The model tries to start a gated skill

- **WHEN** a model on Claude Code or OpenCode tries to load `iwe-ship` or either
  coordinator without a user request
- **THEN** the harness withholds it.
```

## Depends on

- [Remove Codex support](20261031-remove-codex.md)
- [Explore proposes only for observed
  problems](20261103-explore-evidence-gate.md)

## Verification

- `bun test ./.agents/plugins/agentdev/tests/opencode/bridge.test.ts`
- `uv run validate_agent_files --recommend . --require-marketplace claude`
- `uv run pytest --collect-only scripts/e2e/iwe-workflows`, then the Task 5
  scenarios with `test_implement` and `test_explore` on Claude Code and OpenCode
  (Task 6), and the Task 8 scenario on both (Task 8).
- `git grep -n "iwe-implement\b" .agents/plugins/agentdev/skills/iwe-explore .agents/plugins/agentdev/agents/iwe-planner.agent.md`
  prints nothing that names Implement as a next step.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Ship: `/agentdev:iwe-ship` and `/agentdev:iwe-ship-all` stay explicit-only.
- `/agentdev:iwe-implement-all` stays explicit-only, and its skill text is
  unchanged: how a coordinator hands plans to peer sessions is not specified
  here, only how a session it asks behaves.
- Ship's and the Shipper's blocker reports, which keep naming
  `/agentdev:iwe-implement`.

## Key references

- `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md › "description: Execute an active plan task-by-task with state"`
  — `description`
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#how-you-run › "/agentdev:iwe-implement"`
  — **In the user's session** mode
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#how-you-run › "/agentdev:iwe-implement-all"`
  — **Dispatched** mode
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#create-or-revise-a-plan › "readiness, and stop before editing implementation code. Plan"`
  — "report readiness, and stop before editing implementation code"
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps › "Report whether the plan was created or revised, any"`
  — step 8's report
- `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md#during-implementation` —
  `## During implementation` handoff
- `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md#rules` — `## Rules`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts › "disable-model-invocation"`
  — `explicitOnly` read from the frontmatter
- `.agents/plugins/agentdev/.opencode-plugin/index.ts › "for (const { name } of explicitOnly) skill[name] ??="`
  — skill `deny`
- `.agents/plugins/agentdev/tests/opencode/bridge.test.ts › "const expected = Object.fromEntries(explicitOnly.map(({ meta"`
  — deny test
- `scripts/e2e/iwe-workflows/scenarios.py::WORKFLOW_SKILL` — `WORKFLOW_SKILL`
- `scripts/e2e/iwe-workflows/harness_opencode.py::OpenCodeServer.run` —
  `OpenCodeServer.run`
- `scripts/e2e/iwe-workflows/harness_opencode.py::OpenCodeServer.prompt` —
  `OpenCodeServer.prompt`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py::test_implement` —
  `test_implement`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py::test_explore` —
  `test_explore`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py::test_implement` —
  `test_implement`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py::test_explore` —
  `test_explore`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py::test_implement_requested`
  — `test_implement_requested`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py::test_implement_requested`
  — `test_implement_requested`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py::test_implement_coordinator_requested`
  — `test_implement_coordinator_requested`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py::test_implement_coordinator_requested`
  — `test_implement_coordinator_requested`
- `docs/knowledge/data/archive/2.0.0/architecture/explicit-only-workflow-agents.md#decision › "Who may start them."`
  — **Who may start them**
- `docs/knowledge/data/archive/2.0.0/architecture/explicit-only-workflow-agents.md#decision › "The gate is explicit-only on both harnesses."`
  — the gate bullet
- `docs/knowledge/data/archive/2.0.0/architecture/explicit-only-workflow-agents.md#decision › "Implement keeps the user's session for a direct run."`
  — **Implement keeps the user's session**
- `docs/knowledge/data/archive/2.0.0/architecture/explicit-only-workflow-agents.md#rejected-alternatives › "Drop the gate and rely on descriptions, for Ship."`
  — **Drop the gate and rely on descriptions, for Ship**
- `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-explore-remains-an-adaptive-thinking-mode`
  — Explore requirement
- `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-plan-creates-or-revises-planning-state-without-implementing`
  — Plan requirement
- `docs/knowledge/data/spec/iwe-workflow-skills.md#scenario-a-durable-spec-is-retired › "and does not leave an empty or orphaned spec document"`
  — Ship and Implement start requirement
