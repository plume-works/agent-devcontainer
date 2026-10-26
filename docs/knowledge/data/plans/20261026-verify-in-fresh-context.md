---
type: plan
created: 2026-10-26
description: Move Verify's rulebook into an iwe-verifier catalog agent that /agentdev:iwe-verify dispatches with a conversation-free prompt and that iwe-shipper follows in place, so every Verify run judges the code from a fresh context.
release:
- features/verification-in-the-main-loop
generated:
  by: claude-code/opus-5.5
  at: 2026-10-26T04:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-ship/SKILL.md
- resource: .agents/plugins/agentdev/bin/install-codex-agents.py
- resource: scripts/e2e/iwe-workflows/scenarios.py
---

# Run Verify from a fresh context

## Context

[Run Verify from a fresh context](../backlog/verify-in-fresh-context.md) is the
backlog task this plan replaces. Ship already rests on the code and the graph
alone: `/agentdev:iwe-ship` dispatches `iwe-shipper` with only the plan key, the
operation, and quoted approvals ([Explicit-only workflow
agents](../architecture/explicit-only-workflow-agents.md)). Verify does not.
`/agentdev:iwe-verify` runs inline in whatever context loads it, so a Verify run
in the session that wrote the code judges that code with the conversation's
claims in view.

The change gives [Verification in the main
loop](../features/verification-in-the-main-loop.md) new behavior: every Verify
run starts from a fresh context. It is the first of two plans. The second, [Let
Implement verify, fix, and revise on its
own](../backlog/autonomous-implement-loop.md), dispatches the agent this plan
creates and stays out of scope here.

## Approach

Verify's rulebook moves, unchanged in substance, into a new `iwe-verifier`
catalog agent, the way the Ship and Implement rulebooks live in `iwe-shipper`
and `iwe-implementer`. The agent body is the rulebook on all three harnesses:
the Claude Code plugin loads it, the Codex installer renders it into
`agentdev-iwe-verifier.toml`, and the OpenCode bridge registers it as a
subagent, each from the same file.

`/agentdev:iwe-verify` becomes a thin dispatcher with two routes:

- **From a session** — build a prompt carrying only the plan key (or audit mode)
  and the user's approvals quoted verbatim, dispatch `iwe-verifier` forwarding
  no conversation, and re-post its report. An approval the verifier needs comes
  back as `Needs decision`, and the user re-runs the skill granting it — the
  Ship pattern.
- **From inside `iwe-shipper`** — the Shipper is already a fresh context and
  stays a leaf, so the skill tells it to read the `iwe-verifier` rulebook and
  follow it in place rather than dispatch. The Shipper keeps invoking the skill
  because a skill can reach the agent file by a plugin-relative link on every
  harness, while an agent body rendered into a Codex TOML cannot.

`iwe-verifier`'s tools are `Bash, Read, Write, Grep, Glob, Skill`. `Write` is
there so the Codex installer gives it a `workspace-write` sandbox — a read-only
verifier cannot run a `## Verification` command that writes caches or a venv.
Report-only stays a rule of the rulebook, as it is today, not a tool boundary.

Rejected:

- **Give `iwe-shipper` the Agent tool and nest the dispatch.** OpenCode refuses
  a nested dispatch at its default depth, and raising it takes an experimental
  key ([Nested subagent dispatch](../architecture/nested-subagent-dispatch.md)).
- **Keep the rulebook in the skill behind a thin agent**, as the Durable
  Knowledge Auditor does with `iwe-audit`. Then the skill is both the rulebook
  and the entry point that must dispatch, so a session loading it already holds
  the rules it would run inline.
- **A Codex sandbox override key read by the installer.** The maintainer chose
  `Write` in the tools list over a new installer contract.
- **Make `/agentdev:iwe-verify` explicit-only.** Verify mutates nothing, and the
  second plan's Implement loop dispatches the agent, not the skill; the gate
  would protect nothing. Verify stays model-invocable.

## Implementation Steps

### Task 1: Create the iwe-verifier agent

**Files:** Create: `.agents/plugins/agentdev/agents/iwe-verifier.agent.md`

- [x] Write `iwe-verifier.agent.md` with `name: iwe-verifier`, tools
  `Bash, Read, Write, Grep, Glob, Skill`, and a `description` naming its two
  callers — dispatched by the `iwe-verify` skill, followed in place by
  `iwe-shipper` — and "never on a description match".
  - **Evidence:** commit "Add the iwe-verifier agent";
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    reports 0 errors, and `uv run pytest .agents/plugins/agentdev/tests` passes
    270, including `test_installs_the_shipped_catalog_agents`.
- [x] Move Steps 1–5 and the Rules of `iwe-verify/SKILL.md` into the agent body
  without changing what they check, add a `## How you run` section covering the
  dispatched mode (fresh context, inputs are the plan key or audit mode plus
  quoted approvals, never wait for a reply, any other prompt content is not
  evidence) and the in-place mode inside `iwe-shipper`, and a `## Report`
  section whose first line is `Ready to ship`, `Blocked`, `Audit`, or
  `Needs decision` with the plan key.
  - **Evidence:** commit "Add the iwe-verifier agent": `iwe-verifier.agent.md`
    `## Steps` 1–5 and `## Rules` carry the moved checks; `## How you run` and
    `## Report` are new; validator 0 errors.
- [x] Replace Verify's "needs the user's go-ahead" for a command with effects
  beyond the working tree by the Shipper's rule: run it only under a quoted
  approval that names it, otherwise stop before it and report the exact command
  under `Needs decision`.
  - **Evidence:** commit "Add the iwe-verifier agent": the side-effect rule in
    `iwe-verifier.agent.md` `## Rules`; validator 0 errors.

### Task 2: Make /agentdev:iwe-verify a dispatcher

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md`

- [x] Rewrite the skill as the two routes in `## Approach`: from a session,
  build the prompt from the request alone (plan key or audit mode, approvals
  quoted verbatim, nothing else from the conversation), dispatch `iwe-verifier`
  forwarding no conversation turns, and re-post its report verbatim; from inside
  `iwe-shipper`, read `../../agents/iwe-verifier.agent.md` and follow it in
  place without dispatching. Keep the skill's `description`.
  - **Evidence:** commit "Make iwe-verify dispatch iwe-verifier":
    `iwe-verify/SKILL.md` `## From a session` and `## From inside iwe-shipper`;
    validator 0 errors; `uv run pytest .agents/plugins/agentdev/tests` passes
    270\.

### Task 3: Have the Shipper follow the verifier rulebook in place

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-shipper.agent.md`

- [x] Rewrite step 3 so the Shipper invokes `/agentdev:iwe-verify` and takes its
  in-place route, following the `iwe-verifier` rulebook in its own context and
  never dispatching an agent; the approval and CRITICAL handling in that step
  stay as they are.
  - **Evidence:** commit "Have iwe-shipper run Verify in place":
    `iwe-shipper.agent.md` step 3; validator 0 errors;
    `uv run pytest .agents/plugins/agentdev/tests` passes 270.

### Task 4: Cover Verify in the e2e suite

**Files:** Modify: `scripts/e2e/iwe-workflows/scenarios.py`,
`scripts/e2e/iwe-workflows/harness_claude.py`,
`scripts/e2e/iwe-workflows/harness_codex.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_codex.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py`

- [ ] Add `VERIFIER = 'iwe-verifier'` and generalize the per-agent dispatch
  helpers (`shipper_prompts`, `shipper_spawns`) to take the agent name.
- [ ] On each harness add `test_verify`: `/agentdev:iwe-verify` on `HELLO_KEY`
  with no approval dispatches `iwe-verifier` once with a prompt naming the plan,
  publishes nothing, commits nothing, and leaves the plan active; on Codex the
  spawn forwards no turns.
- [ ] On each harness add `test_verify_approved`: the same request with
  `APPROVAL` and `PLANTED` quotes the approval, leaves the planted sentence out,
  runs the publish, commits nothing, and leaves the plan active.
- [ ] In each harness's `test_ship_approved`, assert no `iwe-verifier` was
  dispatched — the Shipper ran Verify in place.

### Task 5: Run the e2e suite on all three harnesses

**Files:** none

- [ ] Run the verify and ship scenarios live on Claude Code, Codex, and OpenCode
  (`## Verification`) and record the result in `## Verification results`.

### Task 6: Record the design and the changed behavior

**Files:** Create: `docs/knowledge/data/architecture/fresh-context-verify.md`;
Modify: `docs/knowledge/data/architecture.md`,
`docs/knowledge/data/features/verification-in-the-main-loop.md`

- [x] Write `data/architecture/fresh-context-verify.md` with the decision in
  `## Approach` and its rejected alternatives, linked from
  `data/architecture.md`.
  - **Evidence:** commit "Record fresh-context Verify in the graph":
    `data/architecture/fresh-context-verify.md`, linked from
    `data/architecture.md`; `iwe normalize` and `iwe schema validate` pass.
- [x] Update `## Behaviour` in [Verification in the main
  loop](../features/verification-in-the-main-loop.md): Verify always runs from a
  fresh context — dispatched by the skill, in place inside the Shipper — and the
  Shipper still consumes the report in its own context.
  - **Evidence:** commit "Record fresh-context Verify in the graph": the
    `## Behaviour` paragraph "Verify always runs from a fresh context" in
    `data/features/verification-in-the-main-loop.md`; `iwe schema validate`
    passes.

### Task 7: Refresh the codebase map

**Files:** Modify: `docs/knowledge/data/codebase/agents/plugins/agentdev.md`,
`docs/knowledge/data/codebase/agents/plugins/agentdev/skills.md`, and any other
doc the map skill reports stale

- [x] Run `/agentdev:iwe-map` refresh mode so the agent list and the skill
  descriptions name `iwe-verifier` and the dispatching `iwe-verify`.
  - **Evidence:** commit "map: refresh the agentdev catalog for iwe-verifier":
    `stale-map-docs.py` reported the two docs `STALE` and ends `RESULT=SUCCESS`
    after the refresh; `iwe schema validate` passes.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — the Verify contract
changes, and it is a requirement's scenario set, so a delta:

``` markdown
## MODIFIED Requirements

### Requirement: Normal shipping requires a clean independent verification

The Ship skill SHALL run the report-only Verify workflow before normal shipping
state changes and SHALL refuse to ship while Verify reports any CRITICAL
finding. Verify SHALL remain independently invocable and SHALL not edit code or
project state. Verify's rulebook SHALL be defined once, as the catalog agent
`iwe-verifier`, and every Verify run SHALL start from a fresh context:
`/agentdev:iwe-verify` SHALL dispatch `iwe-verifier` with a prompt carrying only
the plan key or audit mode and the user's approvals quoted verbatim, and
`iwe-shipper` SHALL follow that rulebook in its own context without dispatching
an agent. Verify SHALL run a verification command whose effects reach beyond
the working tree only under a quoted approval that names it, and otherwise SHALL
stop before it and report the approval it needs.

#### Scenario: Verification reports no critical findings

- **WHEN** Ship invokes Verify for a completed plan and Verify returns zero
  CRITICAL findings
- **THEN** Ship may proceed to spec synchronization and later durable state
  transitions

#### Scenario: Verification reports a critical finding

- **WHEN** Ship invokes Verify and Verify reports one or more CRITICAL findings
- **THEN** Ship makes no shipping state transition and reports the blockers

#### Scenario: A plan is cancelled rather than shipped

- **WHEN** the user explicitly cancels an active plan
- **THEN** Ship records cancellation without requiring implementation
  verification or spec synchronization and performs no release or
  implemented-feature transition

#### Scenario: Verify is invoked outside Ship

- **WHEN** the user requests a mid-implementation check or a workspace audit
- **THEN** the skill dispatches `iwe-verifier`, which produces its
  evidence-backed report and stops without invoking Ship or mutating the graph

#### Scenario: The user verifies a plan without an approval

- **WHEN** the user runs `/agentdev:iwe-verify <plan>` and a `## Verification`
  command reaches beyond the working tree
- **THEN** the dispatch prompt carries the plan key and nothing else from the
  conversation, and `iwe-verifier` stops before that command and reports the
  approval it needs

#### Scenario: The user verifies a plan with an approval

- **WHEN** the user re-runs `/agentdev:iwe-verify <plan>` granting the approval
  the verifier reported, alongside other claims about the work
- **THEN** the dispatch prompt quotes the approval verbatim and leaves the other
  claims out, and `iwe-verifier` runs the approved command

#### Scenario: Ship runs Verify in place

- **WHEN** `iwe-shipper` reaches its Verify step
- **THEN** it follows the `iwe-verifier` rulebook in its own context and
  dispatches no agent
```

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
- `uv run pytest .agents/plugins/agentdev/tests`
- `CODEX_HOME=./.tmp/codex-home uv run .agents/plugins/agentdev/bin/install-codex-agents.py`
  writes `./.tmp/codex-home/agents/agentdev-iwe-verifier.toml` with
  `sandbox_mode = "workspace-write"`.
- `E2E_RUN_LIVE=1 uv run pytest scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py -k 'verify or ship'`,
  and the same for `test_iwe_workflows_codex.py` and
  `test_iwe_workflows_opencode.py` — each spends model usage.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Implement dispatching `iwe-verifier`, acting on its findings, or revising the
  plan — [Let Implement verify, fix, and revise on its
  own](../backlog/autonomous-implement-loop.md).
- Nested dispatch from any catalog agent, and OpenCode's
  `experimental.subagent_depth`.
- Changing the Codex installer's sandbox rule.
- Gating `/agentdev:iwe-verify` as explicit-only.

## Key references

Verified anchor points (line numbers as of 2026-10-26):

- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:14` — `## Steps`, the
  rulebook that moves (Steps 1–5 through line 92)
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:94` — `## Rules`
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:4` — the Shipper's
  `tools:`, without `Agent`
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:71` — step 3, "Run
  Verify for normal shipping"
- `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md:13` — the
  plugin-relative link to an agent rulebook that the skill follows in place
- `.agents/plugins/agentdev/bin/install-codex-agents.py:73` — `render_agent`,
  which derives `sandbox_mode` from `Edit`/`Write` in the tools
- `scripts/e2e/iwe-workflows/scenarios.py:19` — `SHIPPER`
- `scripts/e2e/iwe-workflows/harness_claude.py:85` — `shipper_prompts`
- `scripts/e2e/iwe-workflows/harness_codex.py:167` — `shipper_spawns`
- `scripts/e2e/iwe-workflows/harness_codex.py:171` — `fresh_spawns`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py:35` — the
  `iwe-shipper` subagent prompt filter
- `docs/knowledge/data/spec/iwe-workflow-skills.md:318` — "Normal shipping
  requires a clean independent verification"
- `docs/knowledge/data/features/verification-in-the-main-loop.md:25` —
  `## Behaviour`
