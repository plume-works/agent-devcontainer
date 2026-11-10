---
type: plan
created: 2026-11-02
release:
- features/agentdev-iwe-workflow-skills
description: Drop the explicit-only gate on the iwe-ship skill so a session or coordinator asked to ship a named plan can start Ship, which still runs as a fresh iwe-shipper subagent, while Explore never starts it and the coordinators stay explicit-only.
sources:
- resource: .agents/plugins/agentdev/skills/iwe-ship/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-explore/SKILL.md
- resource: .agents/plugins/agentdev/tests/opencode/bridge.test.ts
- resource: openspec/specs/iwe-workflow-skills/spec.md
stage: cancelled
---

# Let any session asked to ship a named plan start Ship

## Context

`/agentdev:iwe-ship` carries `disable-model-invocation: true`, so a session a
coordinator asked to ship a plan is refused, and the user types the command in
that session. [Let any session asked to implement a named plan start
Implement](20261031-model-invocable-implement.md) removes the same gate from
Implement and keeps it on Ship.

The maintainer decided Ship no longer needs the gate: it exists to keep
conversation context out of Ship, and Ship already runs as a fresh `iwe-shipper`
subagent whose prompt carries only the plan key, the operation, and quoted
approvals.

A coordinator may ask a session to ship a plan and relay the user's approvals:
it asks the user its questions in one place and passes the answers to the
sessions it runs. The skill quotes a relayed approval into the dispatch prompt
the same way as one the user typed.

This reverses an alternative [Explicit-only workflow
agents](../../../../openspec/specs/iwe-workflow-skills/spec.md#rationale)
rejected for Ship: "Drop the gate and rely on descriptions", because a
description match could start Ship from Explore after a partial answer closes a
plan's open question. This plan answers that risk the way the Implement plan
does — a description narrowed to a request that names a plan, and an explicit
Explore rule — instead of with the gate. The released behaviour is in [IWE
workflow skills in the agentdev
catalog](../features/agentdev-iwe-workflow-skills.md).

## Approach

Remove `disable-model-invocation` from `iwe-ship` and narrow its description to
a request that names a plan to ship or cancel, or a release to cut. The skill
body is unchanged: it builds the conversation-free prompt and dispatches
`iwe-shipper`. `iwe-ship-all` and `iwe-implement-all` stay explicit-only.
Explore gains a rule that it never loads Ship.

Rejected:

- **Let a coordinator dispatch `iwe-shipper` directly, keeping the gate.** It
  duplicates the skill's prompt-building rules in every coordinator.

## Implementation Steps

### Task 1: Remove the gate from iwe-ship

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-ship/SKILL.md`,
`.agents/plugins/agentdev/tests/opencode/bridge.test.ts`

- [ ] `SKILL.md` carries no `disable-model-invocation` key.
- [ ] The description says the skill is for a request that names a plan to ship
  or cancel, or a release to cut.
- [ ] Step 1 quotes each approval in the request verbatim, whether the user gave
  it in this session or a coordinator's message relays it from the user.
- [ ] The bridge tests that expect `iwe-ship` denied expect a gated coordinator
  denied instead, and `iwe-ship` allowed.
- [ ] `bun test .agents/plugins/agentdev/tests/opencode/bridge.test.ts` passes.

### Task 2: Explore never starts Ship

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md`

- [ ] `## Rules` says Explore never loads `/agentdev:iwe-ship` or dispatches
  `iwe-shipper`.

### Task 3: Record the decision

**Files:** Modify:
`docs/knowledge/data/architecture/explicit-only-workflow-agents.md`

- [ ] **Who may start them** lists any session asked to ship a named plan, and
  the gate bullet names only the two coordinators as explicit-only.
- [ ] The authority rule says a coordinator may relay the user's approvals to a
  session it asks to ship a plan.
- [ ] The decision states why Ship can drop the gate: it always runs as a fresh
  subagent with a conversation-free prompt, and Explore never starts it.
- [ ] **Drop the gate and rely on descriptions** stays rejected for the
  coordinators only.

### Task 4: Observe a plain-words Ship request on both harnesses

**Closed by:** the maintainer, observing one session on Claude Code and one on
OpenCode with the default test models.

- [ ] A plain prompt asking to ship a named plan, with no command, loads the
  `iwe-ship` skill and dispatches one `iwe-shipper` whose prompt carries only
  the plan key, the ship operation, and quoted approvals.

### Task 5: Observe Explore leaving Ship alone on both harnesses

**Closed by:** the maintainer, observing one session on Claude Code and one on
OpenCode with the default test models.

- [ ] During `/agentdev:iwe-explore`, a partial answer that leaves a plan
  apparently complete loads no Ship or Implement skill and dispatches no
  `iwe-shipper`.

## Spec changes

[IWE workflow skills](../../../../openspec/specs/iwe-workflow-skills/spec.md) —
the requirement on who starts Ship and Implement is modified from the wording
[Let any session asked to implement a named plan start
Implement](20261031-model-invocable-implement.md) records.

``` markdown
## MODIFIED Requirements

### Requirement: Ship and Implement start only from an explicit request or a named dispatcher

The Ship and Implement workflows SHALL each be defined once, as the catalog
agents `iwe-shipper` and `iwe-implementer`. The `iwe-ship-all` and
`iwe-implement-all` coordinators SHALL be explicit-only on Claude Code and
OpenCode. Ship's and Implement's entry skills SHALL be model-invocable on both,
so a session asked to ship or implement a named plan may load them, including
on a message from a coordinator session. Only those skills, those coordinators,
and Plan revise mode answering a Ship blocker report SHALL start the workflows,
and Explore SHALL start neither. Ship SHALL always run as a dispatched
`iwe-shipper` whose prompt carries only the plan key, the operation, and the
user's approvals quoted verbatim, including approvals a coordinator session
relays from the user, so its verification rests on the code and the graph alone.
Implement started through its entry skill SHALL run in the session that loaded
it and SHALL take every decision from that session's own user or from an
approval of the user's that a coordinator session relays. A
dispatched workflow SHALL stop and report at any point that needs a user
decision it was not given.

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

#### Scenario: A session is asked in plain words to ship a plan

- **WHEN** a user or a coordinator session asks a session to ship a named plan
  without typing the command
- **THEN** the session loads `/agentdev:iwe-ship`, which dispatches
  `iwe-shipper` with the plan key and the ship operation and nothing else from
  the conversation.

#### Scenario: A coordinator relays an approval to Ship

- **WHEN** a coordinator session asks a session to ship a named plan and relays
  the user's approval of a command the Shipper reported needing
- **THEN** the session loads `/agentdev:iwe-ship`, the dispatch prompt quotes
  that approval verbatim, and the Shipper runs the approved command.

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
  implement a named plan and relaying the user's approval of a narrowing
  deviation, and a task needs that deviation
- **THEN** the session loads `/agentdev:iwe-implement`, follows the
  `iwe-implementer` rulebook in place, and takes the deviation without asking
  again.

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

#### Scenario: The model tries to start a gated coordinator

- **WHEN** a model on Claude Code or OpenCode tries to load `iwe-ship-all` or
  `iwe-implement-all` without a user request
- **THEN** the harness withholds it.
```

## Depends on

- [Let any session asked to implement a named plan start
  Implement](20261031-model-invocable-implement.md)

## Verification

- `bun test .agents/plugins/agentdev/tests/opencode/bridge.test.ts`
- `uv run validate_agent_files --recommend . --require-marketplace claude`
- Tasks 4 and 5 are observation tasks the maintainer closes; Ship waits for
  them.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- `iwe-ship-all` and `iwe-implement-all` stay explicit-only.
- Having a coordinator start Ship automatically after implementation; this plan
  only allows it.
- The Shipper rulebook and its dispatch prompt — unchanged.

## Key references

- `.agents/plugins/agentdev/skills/iwe-ship/SKILL.md › "description: Close or cancel planned work safely — normal"`
  — `description`
- `.agents/plugins/agentdev/skills/iwe-ship/SKILL.md › "disable-model-invocation: true"`
  — `disable-model-invocation: true`
- `.agents/plugins/agentdev/skills/iwe-ship/SKILL.md#rules › "Never perform a Ship step in this session — no spec merge"`
  — "Never perform a Ship step in this session"
- `.agents/plugins/agentdev/tests/opencode/bridge.test.ts › "const expected = Object.fromEntries(explicitOnly.map(({ meta"`
  — explicit-only skills map to `deny`
- `.agents/plugins/agentdev/tests/opencode/bridge.test.ts › "expect(config.permission.skill"`
  — `iwe-ship` expected `deny`
- `.agents/plugins/agentdev/tests/opencode/bridge.test.ts › "expect(config.permission.skill"`
  — `iwe-ship` expected `deny`
- `docs/knowledge/data/architecture/explicit-only-workflow-agents.md#decision › "Who may start them."`
  — **Who may start them**
- `docs/knowledge/data/architecture/explicit-only-workflow-agents.md#decision › "The gate is explicit-only on both harnesses."`
  — the gate bullet
- `docs/knowledge/data/architecture/explicit-only-workflow-agents.md#rejected-alternatives › "Drop the gate and rely on descriptions, for Ship."`
  — **Drop the gate and rely on descriptions, for Ship**
- `docs/knowledge/data/spec/iwe-workflow-skills.md#scenario-shipping-resumes-after-partial-graph-updates › "incomplete operation"`
  — Ship and Implement start requirement
