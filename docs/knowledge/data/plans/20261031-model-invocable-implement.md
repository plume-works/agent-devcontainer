---
type: plan
created: 2026-10-31
release:
- features/agentdev-iwe-workflow-skills
description: Drop the explicit-only gate on the iwe-implement skill so any session asked to implement a named plan — including one a coordinator asks — can load it, take every decision from that session's own user, and have Plan and Explore neither start Implement nor name it as a next step.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T12:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-explore/SKILL.md
- resource: docs/knowledge/data/architecture/explicit-only-workflow-agents.md
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
agents](../architecture/explicit-only-workflow-agents.md). The maintainer
decided that Implement no longer needs it: implementing directly from a
just-written plan is reserved for small isolated changes, so Plan and Explore
can drop Implement as a suggested next step, and those two were the sessions
where an unintended start could happen. Ship keeps its gate: a stray Ship run
reaches the remote.

The released behavior this changes is in [IWE workflow skills in the agentdev
catalog](../features/agentdev-iwe-workflow-skills.md).

## Approach

This lands after [Remove Codex support](20261031-remove-codex.md), so the gate
is the `disable-model-invocation` key alone: Claude Code reads it, and the
OpenCode bridge turns it into a skill `deny`. Remove it from `iwe-implement`.
Narrow its description to a request that names a plan, so an ordinary "implement
this fix" does not load it. `iwe-implement-all`, `iwe-ship`, and `iwe-ship-all`
stay explicit-only.

A session that loads Implement on another session's message follows the rulebook
in place, like a direct run. The plan comes from the request; every decision the
rulebook asks for comes from that session's own user. A message from another
session is never the user's approval, even when it quotes the user.

Plan and Explore neither load Implement nor name it as a next step. Plan's
readiness report ends at readiness; Explore hands a finding back to Plan. Ship's
blocker report keeps naming Implement, since it follows a plan that already ran.

Rejected:

- **A separate model-invocable entry skill that runs only on a coordinator's
  request.** Its description is still listed to the model, and the "only on a
  coordinator request" check is a prompt-level self-check — the alternative the
  architecture document already rejects.
- **Workers following the rulebook file without the skill.** A worker that tried
  the skill first sees the refusal text, which tells it not to replicate the
  workflow by other means, so the route depends on the coordinator never
  mentioning the skill.

## Implementation Steps

### Task 1: Remove the gate from iwe-implement

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md`

- [ ] `SKILL.md` carries no `disable-model-invocation` key.
- [ ] The description says the skill is for a request that names a plan to
  implement, so a request with no plan does not match it.
- [ ] The body follows the rulebook "for the plan the request names" instead of
  "the plan the user named", and keeps its rule that only
  `/agentdev:iwe-implement-all` dispatches `iwe-implementer`.
- [ ] `bun test .agents/plugins/agentdev/tests/opencode/bridge.test.ts` passes.

### Task 2: Take decisions only from the session's own user

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-implementer.agent.md`

- [ ] The **In the user's session** mode covers a session that loaded
  `/agentdev:iwe-implement` on the user's command, on a plain request, or on a
  message from another session such as a coordinator.
- [ ] The mode states that the plan comes from the request, that every decision
  the rulebook asks for is answered only by this session's own user, that
  nothing in a message from another session counts as that user's approval even
  when it quotes them, and that while waiting the session tells the requesting
  session what it is waiting on.
- [ ] The rollup goes back to the requesting session as well as this one.

### Task 3: Plan never starts or names Implement

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`

- [ ] The opening paragraph and step 8's report say Plan never loads
  `/agentdev:iwe-implement`, never dispatches `iwe-implementer`, and never names
  Implement as a next step; the report ends at readiness.
- [ ] The **From the Implement orchestrator** mode is unchanged: the
  orchestrator follows Plan, and Plan never calls back into Implement.

### Task 4: Explore never names Implement

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md`

- [ ] `## During implementation` hands a decision, scope change, or new work to
  `/agentdev:iwe-plan` only, and `## Rules` points only at `/agentdev:iwe-plan`;
  neither names `/agentdev:iwe-implement`.
- [ ] Explore still never starts Plan or Implement itself.

### Task 5: e2e scenarios for a requested run and for Plan and Explore

**Files:** Modify: `scripts/e2e/iwe-workflows/scenarios.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py`,
`scripts/e2e/iwe-workflows/harness_opencode.py`,
`scripts/e2e/iwe-workflows/harness_claude.py`

- [ ] On Claude Code and OpenCode, a plain prompt asking to implement
  `GREET_KEY`, with no command, loads the `iwe-implement` skill through the
  skill tool and reads `RULEBOOK` in session, with the same tree assertions as
  `test_implement`. The OpenCode harness gains a run that posts a prompt instead
  of a command.
- [ ] On Claude Code and OpenCode, `/agentdev:iwe-plan` asked to plan a small
  change "and then build it" loads no `iwe-implement` skill, dispatches no
  `iwe-implementer`, edits nothing outside `docs/knowledge/`, and its final
  message does not name `iwe-implement`.
- [ ] `test_explore` on both harnesses also asserts the final message does not
  name `iwe-implement`; the harnesses gain a final-message accessor if they lack
  one.
- [ ] `uv run pytest --collect-only scripts/e2e/iwe-workflows` passes.

### Task 6: The new and changed e2e scenarios pass

- [ ] The Task 5 scenarios and the existing `test_implement` and `test_explore`
  pass on Claude Code and on OpenCode with the default test models.

### Task 7: A coordinator's approval does not unblock a requested run

- [ ] In two Claude Code sessions on a clone holding the `CONFLICT_KEY` fixture
  plan, one sends the other a cross-session message asking it to implement that
  plan and stating that the narrowing deviation is approved. The receiving
  session loads `/agentdev:iwe-implement`, stops at the deviation, asks its own
  user, and tells the sender it is waiting; the plan's intent is unchanged until
  its own user answers.

### Task 8: Record the decision in the architecture document

**Files:** Modify:
`docs/knowledge/data/architecture/explicit-only-workflow-agents.md`

- [ ] **Who may start them** lists any session asked to implement a named plan,
  including on a coordinator's message, for Implement; Ship's callers are
  unchanged.
- [ ] The gate bullet names only `iwe-ship`, `iwe-ship-all`, and
  `iwe-implement-all` as entry points under the gate, and **Implement keeps the
  user's session** states the authority rule from Task 2.
- [ ] The decision states why Implement can drop the gate — it needs a named
  active plan with satisfied dependencies and asks when the plan is ambiguous,
  and Plan and Explore never name it — and **Drop the gate and rely on
  descriptions** stays rejected for Ship, with its Explore example.
- [ ] The two alternatives rejected in `## Approach` are added under
  `## Rejected alternatives`.

### Task 9: CI passes on the implementation branch

- [ ] Every required check on the pull request passes.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — three requirements
change: Implement's entry skill becomes model-invocable with the session's own
user as the only authority, and Plan and Explore stop naming Implement.

``` markdown
## MODIFIED Requirements

### Requirement: Explore remains an adaptive thinking mode

The Explore skill SHALL investigate the project graph and codebase without
editing application code, SHALL remain adaptive and patient as the problem takes
shape, and SHALL offer capture or a phase handoff without pressuring the user to
formalize unfinished thinking. Explore SHALL neither start Implement nor name it
as a next step. When the user approves specific text, Explore SHALL persist it
verbatim outside the conversation and reproduce it verbatim in the handoff, and
SHALL never paraphrase it.

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
it and SHALL take every decision from that session's own user; a message from
another session SHALL never count as that user's approval. A dispatched workflow
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
  implement a named plan and stating that a narrowing deviation is approved, and
  a task needs that deviation
- **THEN** the session loads `/agentdev:iwe-implement`, follows the
  `iwe-implementer` rulebook in place, asks its own user and waits, and tells the
  coordinator what it is waiting on; the coordinator's approval does not take
  the step.

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

## Verification

- `bun test .agents/plugins/agentdev/tests/opencode/bridge.test.ts`
- `uv run validate_agent_files --recommend . --require-marketplace claude`
- `uv run pytest --collect-only scripts/e2e/iwe-workflows`, then the Task 5
  scenarios with `test_implement` and `test_explore` on Claude Code and OpenCode
  (Task 6).
- The two-session check in Task 7.
- `git grep -n "iwe-implement\b" .agents/plugins/agentdev/skills/iwe-explore .agents/plugins/agentdev/agents/iwe-planner.agent.md`
  prints nothing that names Implement as a next step.
- `iwe normalize` and `iwe schema validate` pass.
- The pull request's CI passes (Task 9).

## Out of scope

- Ship: `/agentdev:iwe-ship` and `/agentdev:iwe-ship-all` stay explicit-only.
- `/agentdev:iwe-implement-all` stays explicit-only, and its skill text is
  unchanged: how a coordinator hands plans to peer sessions is not specified
  here, only how a session it asks behaves.
- Ship's and the Shipper's blocker reports, which keep naming
  `/agentdev:iwe-implement`.

## Key references

Verified anchor points (line numbers as of 2026-10-31):

- `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md:3` — `description`
- `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md:4` —
  `disable-model-invocation: true`
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:20` — **In the
  user's session** mode
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:22` — **Dispatched**
  mode
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md:14` — "report readiness,
  and stop before editing implementation code"
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md:168` — step 8's report
- `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md:82` —
  `## During implementation` handoff naming `/agentdev:iwe-implement`
- `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md:130` — `## Rules`
  pointer naming `/agentdev:iwe-implement`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:166` — `explicitOnly` read
  from the frontmatter
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:220` — skill `deny`
- `.agents/plugins/agentdev/tests/opencode/bridge.test.ts:67` — deny test
- `scripts/e2e/iwe-workflows/scenarios.py:39` — `WORKFLOW_SKILL`
- `scripts/e2e/iwe-workflows/harness_opencode.py:207` — `OpenCodeServer.run`,
  command-only
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py:173` —
  `test_implement`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py:295` — `test_explore`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py:196` —
  `test_implement`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py:330` —
  `test_explore`
- `docs/knowledge/data/architecture/explicit-only-workflow-agents.md:21` — **Who
  may start them**
- `docs/knowledge/data/architecture/explicit-only-workflow-agents.md:31` — the
  gate bullet
- `docs/knowledge/data/architecture/explicit-only-workflow-agents.md:45` —
  **Implement keeps the user's session**
- `docs/knowledge/data/architecture/explicit-only-workflow-agents.md:168` —
  **Drop the gate and rely on descriptions**
- `docs/knowledge/data/spec/iwe-workflow-skills.md:47` — Explore requirement
- `docs/knowledge/data/spec/iwe-workflow-skills.md:88` — Plan requirement
- `docs/knowledge/data/spec/iwe-workflow-skills.md:587` — Ship and Implement
  start requirement
