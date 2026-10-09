---
type: plan
created: 2026-10-07
description: Move the Ship and Implement workflows into catalog agents that coordinators dispatch by name, run Ship always as a subagent with a conversation-free prompt, keep their user entry skills and the coordinators explicit-only on Claude, Codex, and OpenCode, and let a plan revision that answers a Ship blocker re-dispatch the Shipper.
generated:
  by: claude-code/opus-5-5
  at: 2026-10-07T15:00:00Z
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
so each gated skill needs that file as well.

A plan revision that answers a Ship blocker should be followed by a fresh Ship
without the user re-invoking it.

## Approach

Each workflow's rulebook moves into a catalog agent — `iwe-shipper` and
`iwe-implementer` — and each caller reaches it by an explicit act:

```
you ──/agentdev:iwe-ship──► iwe-ship (explicit-only) ──dispatch──► iwe-shipper subagent
you ──/agentdev:iwe-implement──► iwe-implement (explicit-only)
                              └─ this session follows agents/iwe-implementer.agent.md
iwe-ship-all (explicit-only) ──dispatch──► iwe-shipper subagent
iwe-plan revise, answering a Ship blocker ──dispatch──► iwe-shipper subagent
iwe-explore ──✘── nothing to match: the skills are explicit-only, the agent is
                  dispatched by name, and its description names its dispatchers
```

- **The agent file is the single rulebook.** A dispatched agent cannot reach the
  user: at any point the rulebook would ask, it stops and reports the decision
  needed.
- **Ship always runs as a subagent.** Its verification must rest only on what
  the code and the graph record, never on what a conversation asserted, so every
  caller — the user's own `/agentdev:iwe-ship` included — dispatches
  `iwe-shipper` with a fresh context.
- **A Shipper dispatch prompt carries nothing from the conversation:** the plan
  key, the operation (ship, cancel, or release `<X.Y.Z>`), and any approval the
  user gave, quoted verbatim. An approval the Shipper needs comes back in its
  report; the user re-runs `/agentdev:iwe-ship` with that approval.
- **Implement keeps the user's session for direct runs.** The
  `/agentdev:iwe-implement` entry skill tells the session to follow the
  `iwe-implementer` rulebook in place, so it can ask about plan ambiguity and a
  material deviation; only `iwe-implement-all` dispatches it.
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
- **The end-to-end checks are rerunnable.** A committed harness builds an
  isolated clone of the repository with fixture plans and drives each harness
  headless, asserting the facts a scenario's THEN clause names — who was
  dispatched, what its prompt carried, and what changed in and outside the
  clone. It lives under `scripts/e2e/<plan key>/`, named after the plan it
  verifies so each harness links back to its plan, and not in the plugin's
  tests: it clones this repository and spends model usage, so it neither runs
  from a consumer's plugin cache nor belongs in a default test run.

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

- [x] Write the decision: agent-owned rulebooks, the three-harness explicit-only
  gate, the callers allowed to dispatch, Ship always dispatched with a prompt
  that carries nothing from the conversation, and each rejected alternative with
  the harness behavior that rules it out, each behavior with the minimal fixture
  and command that reproduces it. Link it from `data/architecture.md`.
  - **Evidence:** committed with this tick; each Claude Code and Codex behavior
    in `data/architecture/explicit-only-workflow-agents` was reproduced with its
    recorded fixture and command on Claude Code 2.1.280 and Codex 0.156.1, and
    `iwe schema validate` passes.

### Task 2: Make the Ship rulebook an agent

**Files:** Create: `.agents/plugins/agentdev/agents/iwe-shipper.agent.md`

- [x] Move the body of `iwe-ship/SKILL.md` into the agent, rewritten to run only
  as a dispatched subagent whose inputs are the plan key, the operation, and
  quoted user approvals. It stops at each point the workflow would ask the user
  — the approval before commands with effects beyond the working tree, an
  operation its prompt does not name — and reports what it needs, unless its
  prompt already carries that approval or operation. A CRITICAL stop reports a
  Ship blocker report naming the plan and the revise route. Its `description`
  names its only dispatchers: the `iwe-ship` skill, the `iwe-ship-all`
  coordinator, and `iwe-plan` revise answering a Ship blocker report. Tools:
  `Bash, Read, Edit, Write, Grep, Glob, Skill`.
  - **Evidence:** implemented in 8841951;
    `uv run validate_agent_files .agents/plugins/agentdev/agents --kind agents --ci`
    exit 0, `test_install_codex_agents.py` 10 passed, and the bridge's
    `bun test` 12 passed.

### Task 3: Make the Implement rulebook an agent

**Files:** Create: `.agents/plugins/agentdev/agents/iwe-implementer.agent.md`

- [x] Move the body of `iwe-implement/SKILL.md` into the agent, rewritten to run
  both in the user's session and as a dispatched subagent. Dispatched, it stops
  on plan ambiguity and on a material deviation and reports them instead of
  waiting. Its `description` names its only dispatchers: the `iwe-implement`
  skill and the `iwe-implement-all` coordinator.
  - **Evidence:** implemented in bc07ccc;
    `uv run validate_agent_files .agents/plugins/agentdev/agents --kind agents --ci`
    exit 0 and the bridge's `bun test` 12 passed.

### Task 4: Reduce the user entry skills to the agents

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-ship/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-implement/SKILL.md`; Create:
`.agents/plugins/agentdev/skills/iwe-ship/agents/openai.yaml`,
`.agents/plugins/agentdev/skills/iwe-implement/agents/openai.yaml`

- [x] Each skill keeps its frontmatter and `disable-model-invocation: true` and
  gains the Codex policy file. `iwe-ship` dispatches `iwe-shipper` with the plan
  key, the operation, and the user's approvals quoted verbatim — no summary of
  the conversation — and re-posts its report. `iwe-implement` directs the
  session to follow the `iwe-implementer` rulebook, located relative to the
  skill directory.
  - **Evidence:** implemented in 9add615;
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    reports 62/62 skills valid with 0 errors and 0 warnings.

### Task 5: Dispatch the agents from the coordinators

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-ship-all/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md`; Create: their
`agents/openai.yaml`

- [x] Each coordinator becomes explicit-only on all three harnesses and
  dispatches `iwe-shipper` or `iwe-implementer` by name per plan, in dependency
  order. Ship-all re-posts each Shipper's Verify verdict with its outcome.
  - **Evidence:** implemented in 5ea1f8a; `validate_agent_files --recommend`
    reports 62/62 skills valid with 0 warnings, and the bridge's `bun test` 12
    passed, its deny and subagent assertions derived from the catalog.

### Task 6: Re-dispatch the Shipper after a revision

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md`

- [x] In revise mode, when the revision answers a Ship blocker report for the
  plan, step 8 dispatches `iwe-shipper` on that plan once validation passes and
  reports its outcome; every other revision stops after validation.
  - **Evidence:** implemented in 2115bbf; `validate_agent_files --recommend`
    reports 62/62 skills valid with 0 warnings.

### Task 7: Gate every explicit-only skill on Codex

**Files:** Create: `agents/openai.yaml` for each remaining skill that sets
`disable-model-invocation: true` (`iwe-plan`, `iwe-setup`, `iwe-weekly`);
Create: `.agents/plugins/agentdev/tests/test_explicit_only_parity.py`

- [x] Add the Codex policy file to each, and a test that fails when a skill sets
  `disable-model-invocation: true` without
  `policy.allow_implicit_invocation: false`, or the reverse.
  - **Evidence:** implemented in 5c18829;
    `uv run pytest .agents/plugins/agentdev/tests/test_explicit_only_parity.py`
    failed on `iwe-plan`, `iwe-setup`, and `iwe-weekly` before their policy
    files and passes 6 after; the plugin suite 130 passed and
    `python-lint-check.sh` is clean.

### Task 8: Claude Code runs the design end to end

- [x] On Claude Code: `/agentdev:iwe-ship-all` dispatches `iwe-shipper` and
  reports its outcome; `/agentdev:iwe-ship` run directly dispatches
  `iwe-shipper` with only the plan key, operation, and quoted approvals, and an
  approval it needs comes back in its report; `/agentdev:iwe-implement` run
  directly asks about a material deviation in the session; and
  `/agentdev:iwe-explore`, given a partial answer that closes a plan's open
  question, neither dispatches the Shipper nor loads a coordinator.
  - **Evidence:** Claude Code 2.1.280 headless (`claude -p --plugin-dir`) on a
    clone of 5c18829 with fixture plans. `/agentdev:iwe-ship` dispatched
    `agentdev:iwe-shipper` with only the plan key, `ship`, and
    `Approvals: none`; the Shipper stopped before the plan's publish command and
    reported the approval, with no mutation. Re-run with the approval quoted, it
    ran the command and shipped. `/agentdev:iwe-ship-all` dispatched the Shipper
    on the one implemented plan and re-posted its Verify verdict and outcome.
    `/agentdev:iwe-implement` read `agents/iwe-implementer.agent.md` in the
    session, dispatched nothing, and asked about a task contradicting its spec
    outcome with the box left unticked. `/agentdev:iwe-explore`, told a fully
    ticked plan's open question was answered, made no Agent or Skill call and
    pointed at `/agentdev:iwe-plan`.

### Task 9: Codex runs the design end to end

- [x] The Task 8 checks pass on Codex, and Codex lists none of `iwe-ship`,
  `iwe-implement`, `iwe-plan`, or either coordinator as implicitly invocable.
  - **Evidence:** Codex 0.156.1 `codex exec -s workspace-write` after
    `reinstall-agentdev-codex.sh` from 1213210, on the Task 8 fixtures. Its
    skill list holds no gated skill. `$agentdev:iwe-ship` and
    `$agentdev:iwe-ship-all` spawned `iwe-shipper` with `fork_turns: "none"`
    (the message itself is stored encrypted); without approval it reported the
    publish command it needed, and with the approval quoted it ran the command,
    which the sandbox's read-only filesystem failed, returning a Ship blocker
    report with no mutation. `$agentdev:iwe-implement` read the rulebook in
    place, spawned nothing, and asked about the deviation.
    `$agentdev:iwe-explore` spawned nothing and ran no Ship or Implement skill.

### Task 10: OpenCode runs the design end to end

- [x] The Task 8 checks pass on OpenCode through the bridge, with a model the
  maintainer uses.
  - **Evidence:** OpenCode 1.18.34 `opencode run -m openai/gpt-6-astra` (the
    maintainer's Codex model and login) through the bridge at b941b6f, on the
    Task 8 fixtures, with `external_directory` granted for the fixture's scratch
    directory and the catalog's `agents/`. `agentdev:iwe-ship` dispatched
    `iwe-shipper` with only the plan key and `ship`, and it stopped for the
    publish approval with no mutation; re-run with the approval quoted verbatim,
    it ran the command. `agentdev:iwe-ship-all` dispatched the Shipper and
    re-posted its Verify verdict and outcome. `agentdev:iwe-implement` read the
    rulebook in place, dispatched nothing, and asked about the deviation.
    `agentdev:iwe-explore` made no task or skill call. Both ships then stopped
    on the plan's missing feature or bug, captured as
    `data/bugs/ship-release-link-without-feature`.

### Task 11: Commit the end-to-end harness

**Files:** Create: `scripts/e2e/20261007-agent-owned-ship-implement/run.sh`,
`scripts/e2e/20261007-agent-owned-ship-implement/fixtures/` (the two fixture
plans, the publish script, and the OpenCode project config)

- [ ] Commit the fixtures and a runner. The fixtures are an implemented plan
  whose `## Verification` runs a publish script whose only effect is a marker
  file outside the clone, and a plan whose one unticked task contradicts its
  recorded spec outcome; the implemented plan also gets a variant that adds an
  answered open question. The runner bundles `HEAD` into a clone under `./.tmp`
  with no remote, commits the fixtures there, and resets the clone between
  checks. It takes the harnesses to run and an OpenCode model as arguments, with
  no model default, and writes each run's raw log under `./.tmp`. It grants
  exactly what each harness needs and nothing wider: Claude Code `--plugin-dir`
  and an `--allowedTools` list naming the fixture commands; Codex
  `-s workspace-write`; OpenCode an `external_directory` allow for the scratch
  directory and the catalog's `agents/`. Each check prints PASS or FAIL per
  assertion, and the runner exits non-zero on any FAIL:

  - ship without approval — one dispatch of `iwe-shipper` carrying the plan key;
    no marker, no commit, plan still active;
  - ship with approval — the dispatch carries the approval sentence verbatim and
    omits a non-approval sentence planted in the same request; the publish
    command ran;
  - ship-all — one dispatch of `iwe-shipper`;
  - implement — the rulebook file was read, nothing was dispatched, the task
    stays unticked and its file absent;
  - explore — no dispatch and no Ship or Implement skill load; no marker, no
    commit;
  - Codex only — no gated catalog skill in its implicit-invocation list.

  Where a harness does not expose a fact, the runner asserts what it does expose
  and says so. `shellcheck` passes.

### Task 12: The harness passes on Claude Code

- [ ] `scripts/e2e/20261007-agent-owned-ship-implement/run.sh` passes every
  Claude Code check.

### Task 13: The harness passes on Codex

- [ ] `scripts/e2e/20261007-agent-owned-ship-implement/run.sh` passes every
  Codex check.

### Task 14: The harness passes on OpenCode

- [ ] `scripts/e2e/20261007-agent-owned-ship-implement/run.sh` passes every
  OpenCode check with a model the maintainer uses.

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
Plan revise mode answering a Ship blocker report SHALL start the workflows.
Ship SHALL always run as a dispatched `iwe-shipper` whose prompt carries only
the plan key, the operation, and the user's approvals quoted verbatim, so its
verification rests on the code and the graph alone. Implement started by the
user's own invocation SHALL run in the user's session. A dispatched workflow
SHALL stop and report at any point that needs a user decision it was not
given.

#### Scenario: The user ships a plan directly

- **WHEN** the user runs `/agentdev:iwe-ship <plan>` with no approval
- **THEN** the skill dispatches `iwe-shipper` with the plan key and the ship
  operation and nothing else from the conversation, and the Shipper stops
  before a command with effects beyond the working tree and reports the
  approval it needs.

#### Scenario: The user ships a plan with an approval

- **WHEN** the user re-runs `/agentdev:iwe-ship <plan>` granting the approval
  the Shipper reported
- **THEN** the dispatch prompt quotes that approval verbatim, and the Shipper
  runs the approved command.

#### Scenario: The user implements a plan directly

- **WHEN** the user runs `/agentdev:iwe-implement <plan>` and a task needs a
  material deviation
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
- `bun test ./.agents/plugins/agentdev/tests/opencode/` — the bridge registers
  both new agents and denies every gated skill.
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
- `iwe normalize` and `iwe schema validate` after the architecture document.
- Tasks 8–10 are the end-to-end checks on each harness.
- `shellcheck scripts/e2e/20261007-agent-owned-ship-implement/run.sh`
- `scripts/e2e/20261007-agent-owned-ship-implement/run.sh` on all three
  harnesses (Tasks 12–14); it needs each CLI authenticated and spends model
  usage.

## Out of scope

- Making `/agentdev:iwe-plan` model-invocable; revise mode stays user-run.
- Verify starting Ship: a standalone Verify still never invokes it.
- Changing what Ship or Implement does beyond where it runs and how it stops.
- A `validate_agent_files` rule for the Codex policy file — the package ships
  independently of this catalog.
- Running the end-to-end harness in CI — it needs each harness's model login.

## Key references

Verified anchor points (line numbers as of 2026-10-09):

- `.agents/plugins/agentdev/skills/iwe-ship/SKILL.md:4` —
  `disable-model-invocation: true`
- `.agents/plugins/agentdev/skills/iwe-ship/SKILL.md:24` — dispatch prompt
  carries nothing else
- `.agents/plugins/agentdev/skills/iwe-ship/SKILL.md:28` — dispatch
  `iwe-shipper`
- `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md:13` — follow the
  `iwe-implementer` rulebook in place
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:34` — stopping for a
  decision
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:166` — Ship blocker
  report
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:15` — session and
  dispatched modes
- `.agents/plugins/agentdev/skills/iwe-ship-all/SKILL.md:13` — dispatch
  `iwe-shipper` per plan
- `.agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md:12` — dispatch
  `iwe-implementer` per plan
- `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md:136` — revise answering a
  Ship blocker re-dispatches the Shipper
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:71` — Verify never
  invokes Ship
- `.agents/plugins/agentdev/skills/create-skill/SKILL.md:48` —
  `policy.allow_implicit_invocation`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:77` — explicit-only skills
  collected for `deny`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:92` — catalog agents
  registered as subagents
- `.agents/plugins/agentdev/tests/test_explicit_only_parity.py:33` — Claude and
  Codex gate parity
- `docs/knowledge/data/architecture/explicit-only-workflow-agents.md:58` — gate
  fixture
- `docs/knowledge/data/architecture/explicit-only-workflow-agents.md:158` —
  OpenCode `external_directory` grant for the catalog
- `docs/knowledge/data/spec/iwe-workflow-skills.md:264` — normal shipping
  requirement
