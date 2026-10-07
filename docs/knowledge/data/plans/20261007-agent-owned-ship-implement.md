---
type: plan
created: 2026-10-07
description: Move the Ship and Implement workflows into catalog agents that coordinators dispatch by name, keep their user entry skills and the coordinators explicit-only on Claude, Codex, and OpenCode, and let a plan revision that answers a Ship blocker re-dispatch the Shipper.
generated:
  by: claude-code/opus-5-5
  at: 2026-10-07T12:30:00Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-ship/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-ship-all/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
- resource: .agents/plugins/agentdev/.opencode-plugin/index.ts
---

# Agent-owned Ship and Implement workflows

## Context

`/agentdev:iwe-ship-all` and `/agentdev:iwe-implement-all` dispatch one subagent
per plan with `/agentdev:iwe-ship <plan>` or `/agentdev:iwe-implement <plan>` as
its prompt. Both target skills set `disable-model-invocation: true`, which bars
every model-initiated load — a subagent's included — so neither coordinator can
run on Claude Code, and the OpenCode bridge's `skill: deny` blocks them the same
way.

The gate keeps Ship from starting on a description match — for example from
Explore, after a partial answer closes a plan's open question. Codex ignores
`disable-model-invocation`: only `agents/openai.yaml` with
`policy.allow_implicit_invocation: false` suppresses implicit invocation there,
and no gated skill ships one, so Codex lists `iwe-ship`, `iwe-implement`, and
`iwe-plan` as implicitly invocable.

A plan revision that answers a Ship blocker should be followed by a fresh Ship
without the user re-invoking it.

## Approach

Each workflow's rulebook moves into a catalog agent — `iwe-shipper` and
`iwe-implementer` — and each caller reaches it by an explicit act:

```
you ──/agentdev:iwe-ship──► iwe-ship (explicit-only)
                              └─ this session follows agents/iwe-shipper.agent.md
iwe-ship-all (explicit-only) ──dispatch──► iwe-shipper subagent
iwe-plan revise, answering a Ship blocker ──dispatch──► iwe-shipper subagent
iwe-explore ──✘── nothing to match: the skills are explicit-only, the agent is
                  dispatched by name, and its description names its dispatchers
```

- **The agent file is the single rulebook.** A user-run entry skill tells the
  session to follow it in place, so the workflow can still ask the user for a
  decision or an approval. A dispatched agent cannot reach the user: at any
  point the rulebook would ask, it stops and reports the decision needed.
- **Explicit-only on all three harnesses.** `disable-model-invocation: true` for
  Claude Code and for the OpenCode bridge's `deny`, plus `agents/openai.yaml`
  with `policy.allow_implicit_invocation: false` for Codex — the case
  `create-skill` already allows the file for. The coordinators get the same
  gate: the user starts them, and an invocable coordinator is the one
  description match left on the path to shipping.
- **Re-ship after revise.** A Ship that stops on a CRITICAL reports a Ship
  blocker report naming the plan. When `/agentdev:iwe-plan` revise mode answers
  such a report, it dispatches `iwe-shipper` on the plan after validation, and
  Ship's own Verify decides again.

Rejected:

- **Drop the gate and rely on descriptions** — a description match can start
  Ship from Explore.
- **Preload the gated skill into the agent** — Claude Code withholds a
  `disable-model-invocation` skill from an agent's `skills:` preload.
- **Rulebook in a reference file the coordinator's subagent reads** — a subagent
  reading a gated skill's file bypasses the gate, which a harness's model may
  rightly refuse as one.
- **A self-checking skill or a harness hook** — a prompt-level check a model can
  argue past; a hook sees a tool call, not who asked for it, so it cannot tell a
  coordinator's dispatch from Explore's, and it needs one implementation per
  harness.

## Implementation Steps

### Task 1: Record the decision

**Files:** Create:
`docs/knowledge/data/architecture/explicit-only-workflow-agents.md`; Modify:
`docs/knowledge/data/architecture.md`

- [ ] Write the decision: agent-owned rulebooks, the three-harness explicit-only
  gate, the callers allowed to dispatch, and each rejected alternative with the
  harness behavior that rules it out. Link it from `data/architecture.md`.

### Task 2: Make the Ship rulebook an agent

**Files:** Create: `.agents/plugins/agentdev/agents/iwe-shipper.agent.md`

- [ ] Move the body of `iwe-ship/SKILL.md` into the agent, rewritten to run both
  in the user's session and as a dispatched subagent. Dispatched, it stops at
  each point the workflow asks the user — the approval before commands with
  effects beyond the working tree, a cancellation, a release cut — and reports
  what it needs. A CRITICAL stop reports a Ship blocker report naming the plan
  and the revise route. Its `description` names its only dispatchers: the
  `iwe-ship` skill, the `iwe-ship-all` coordinator, and `iwe-plan` revise
  answering a Ship blocker report. Tools:
  `Bash, Read, Edit, Write, Grep, Glob, Skill`.

### Task 3: Make the Implement rulebook an agent

**Files:** Create: `.agents/plugins/agentdev/agents/iwe-implementer.agent.md`

- [ ] Move the body of `iwe-implement/SKILL.md` into the agent the same way.
  Dispatched, it stops on plan ambiguity and on a material deviation and reports
  them instead of waiting. Its `description` names its only dispatchers: the
  `iwe-implement` skill and the `iwe-implement-all` coordinator.

### Task 4: Reduce the user entry skills to the agents

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-ship/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-implement/SKILL.md`; Create:
`.agents/plugins/agentdev/skills/iwe-ship/agents/openai.yaml`,
`.agents/plugins/agentdev/skills/iwe-implement/agents/openai.yaml`

- [ ] Each skill keeps its frontmatter and `disable-model-invocation: true`,
  gains the Codex policy file, and its body directs the session to follow its
  agent's rulebook, located relative to the skill directory.

### Task 5: Dispatch the agents from the coordinators

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-ship-all/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md`; Create: their
`agents/openai.yaml`

- [ ] Each coordinator becomes explicit-only on all three harnesses and
  dispatches `iwe-shipper` or `iwe-implementer` by name per plan, in dependency
  order. Ship-all re-posts each Shipper's Verify verdict with its outcome.

### Task 6: Re-dispatch the Shipper after a revision

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md`

- [ ] In revise mode, when the revision answers a Ship blocker report for the
  plan, step 8 dispatches `iwe-shipper` on that plan once validation passes and
  reports its outcome; every other revision stops as it does now.

### Task 7: Gate every explicit-only skill on Codex

**Files:** Create: `agents/openai.yaml` for each remaining skill that sets
`disable-model-invocation: true` (`iwe-plan`, `iwe-setup`, `iwe-weekly`);
Create: `.agents/plugins/agentdev/tests/test_explicit_only_parity.py`

- [ ] Add the Codex policy file to each, and a test that fails when a skill sets
  `disable-model-invocation: true` without
  `policy.allow_implicit_invocation: false`, or the reverse.

### Task 8: Claude Code runs the design end to end

- [ ] On Claude Code: `/agentdev:iwe-ship-all` dispatches `iwe-shipper` and
  reports its outcome; `/agentdev:iwe-ship` run directly asks for approval in
  the session; and `/agentdev:iwe-explore`, given a partial answer that closes a
  plan's open question, neither dispatches the Shipper nor loads a coordinator.

### Task 9: Codex runs the design end to end

- [ ] The Task 8 checks pass on Codex, and Codex no longer lists `iwe-ship`,
  `iwe-implement`, `iwe-plan`, or either coordinator as implicitly invocable.

### Task 10: OpenCode runs the design end to end

- [ ] The Task 8 checks pass on OpenCode through the bridge, with a model the
  maintainer uses.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — who may start Ship and
Implement is a contract across three harnesses:

``` markdown
## ADDED Requirements

### Requirement: Ship and Implement start only from an explicit request or a named dispatcher

The Ship and Implement workflows SHALL each be defined once, as the catalog
agents `iwe-shipper` and `iwe-implementer`. Their user entry skills and the
`iwe-ship-all` and `iwe-implement-all` coordinators SHALL be explicit-only on
Claude Code, Codex, and OpenCode. Only those skills, those coordinators, and
Plan revise mode answering a Ship blocker report SHALL start the workflows. A
workflow started by the user's own invocation SHALL run in the user's session;
a dispatched workflow SHALL stop and report at any point that needs a user
decision.

#### Scenario: The user ships a plan directly

- **WHEN** the user runs `/agentdev:iwe-ship <plan>`
- **THEN** the session follows the `iwe-shipper` rulebook and asks the user for
  approval before a command with effects beyond the working tree.

#### Scenario: A coordinator ships every implemented plan

- **WHEN** the user runs `/agentdev:iwe-ship-all`
- **THEN** it dispatches one `iwe-shipper` agent per implemented plan in
  dependency order and re-posts each one's Verify verdict and outcome.

#### Scenario: A dispatched workflow reaches a user decision

- **WHEN** a dispatched `iwe-shipper` or `iwe-implementer` reaches a point that
  needs the user
- **THEN** it stops without taking that step and reports what it needs.

#### Scenario: Explore hears a partial answer to an open question

- **WHEN** during `/agentdev:iwe-explore` the user answers an open question in
  a way that leaves a plan apparently complete
- **THEN** Explore neither dispatches `iwe-shipper` nor loads a Ship or
  Implement skill or coordinator, and names the next step for the user.

#### Scenario: A revision answers a Ship blocker

- **WHEN** `/agentdev:iwe-plan` revise mode changes a plan to answer the Ship
  blocker report Ship returned for it, and validation passes
- **THEN** Plan dispatches `iwe-shipper` on that plan, whose Verify decides
  whether it ships.

#### Scenario: The model tries to start a gated skill

- **WHEN** a model on Claude Code, Codex, or OpenCode tries to load
  `iwe-ship`, `iwe-implement`, or either coordinator without a user request
- **THEN** the harness withholds it.
```

## Depends on

[Install the catalog agents into Codex](20261007-codex-catalog-agents.md)

## Verification

- `uv run pytest .agents/plugins/agentdev/tests/test_explicit_only_parity.py`
- `bun test .agents/plugins/agentdev/tests/opencode/` — the bridge registers
  both new agents and denies every gated skill.
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
- `iwe normalize` and `iwe schema validate` after the architecture document.
- Tasks 8–10 are the end-to-end checks on each harness.

## Out of scope

- Making `/agentdev:iwe-plan` model-invocable; revise mode stays user-run.
- Verify starting Ship: a standalone Verify still never invokes it.
- Changing what Ship or Implement does beyond where it runs and how it stops.
- A `validate_agent_files` rule for the Codex policy file — the package ships
  independently of this catalog.

## Key references

Verified anchor points (line numbers as of 2026-10-07):

- `.agents/plugins/agentdev/skills/iwe-ship/SKILL.md:4` —
  `disable-model-invocation: true`
- `.agents/plugins/agentdev/skills/iwe-ship/SKILL.md:39` — approval before
  commands beyond the working tree
- `.agents/plugins/agentdev/skills/iwe-ship/SKILL.md:41` — CRITICAL stop, no
  override
- `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md:4` —
  `disable-model-invocation: true`
- `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md:17` — plan selection,
  asks when ambiguous
- `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md:68` — material
  deviation waits for the user
- `.agents/plugins/agentdev/skills/iwe-ship-all/SKILL.md:8` — coordinator prompt
- `.agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md:8` — coordinator
  prompt
- `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md:121` — step 8, validate and
  stop
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:71` — Verify never
  invokes Ship
- `.agents/plugins/agentdev/skills/create-skill/SKILL.md:48` —
  `policy.allow_implicit_invocation`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:77` — explicit-only skills
  collected for `deny`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:92` — catalog agents
  registered as subagents
- `docs/knowledge/data/spec/iwe-workflow-skills.md:264` — normal shipping
  requirement
