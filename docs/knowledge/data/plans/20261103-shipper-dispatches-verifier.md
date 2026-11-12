---
type: plan
created: 2026-11-03
release:
- features/verification-in-the-main-loop
description: Give iwe-shipper the Agent tool so its Verify step runs through the iwe-verify skill's dispatch route, keeping every Verify run out of the Shipper's context, and retire the in-place route.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: docs/knowledge/data/architecture/fresh-context-verify.md
rank: 300
---

# The Shipper dispatches Verify

## Context

[Run Verify from the iwe-ship skill, not inside the
Shipper](../backlog/ship-verifies-before-dispatch.md) is the backlog task this
plan replaces. On a saved-report miss, `iwe-shipper` follows the `iwe-verifier`
rulebook in its own context, so the whole Verify run sits in the Shipper's
context ahead of the steps that change the graph.

The backlog task proposed `/agentdev:iwe-ship` dispatching `iwe-verifier` before
the Shipper. Once [Nest agent dispatch to depth 5 on both
harnesses](20261103-nested-dispatch-depth.md) lets a dispatched agent dispatch
another, the repository owner chose instead that `iwe-shipper` dispatches
`iwe-verifier` itself. Every route that dispatches the Shipper —
`/agentdev:iwe-ship` and `/agentdev:iwe-plan` answering a Ship blocker report —
then gets a fresh-context Verify with no change of its own. This reverses the
in-place route [Fresh-context Verify](../architecture/fresh-context-verify.md)
chose to keep the Shipper a leaf. The change gives [Verification in the main
loop](../features/verification-in-the-main-loop.md) new behavior.

## Approach

`iwe-shipper` gains the `Agent` tool. Its step 3 runs `/agentdev:iwe-verify` by
the skill's session route — look up the saved report, on a miss dispatch
`iwe-verifier` with the plan key and the approvals the Shipper's prompt quotes,
then save its report — so only the report enters the Shipper's context. The
skill's "From inside `iwe-shipper`" route and the `iwe-verifier` rulebook's "In
place inside `iwe-shipper`" mode are removed.

Rejected: `/agentdev:iwe-ship` dispatching `iwe-verifier` before `iwe-shipper`,
as the backlog task proposed. `/agentdev:iwe-plan`'s re-dispatch would need the
same step.

## Implementation Steps

### Task 1: The Shipper dispatches Verify

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-shipper.agent.md`

- [x] `tools:` includes `Agent`, and step 3 runs `/agentdev:iwe-verify` by its
  session route, forwarding the approvals its prompt quotes verbatim, instead of
  following the `iwe-verifier` rulebook in place; the line saying it never
  dispatches an agent is replaced.
  - **Evidence:**
    `.agents/plugins/agentdev/agents/iwe-shipper.agent.md › "tools: Bash, Read, Edit, Write, Grep, Glob, Skill, Agent"`
    and
    `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps › "and take its session route"`;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes.

### Task 2: Verify has one route

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md`,
`.agents/plugins/agentdev/agents/iwe-verifier.agent.md`

- [x] `/agentdev:iwe-verify` drops its "From inside `iwe-shipper`" section, and
  its session route names the Shipper as a caller whose skill request and
  verifier prompt are the plan key and the approvals the Shipper's prompt
  quotes.
  - **Evidence:**
    `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md#from-a-session › "the request is the plan you are shipping"`
    and
    `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md#the-saved-report › "the Implement loop or the Shipper"`;
    the "From inside `iwe-shipper`" section is gone.
- [x] `iwe-verifier` drops its "In place inside `iwe-shipper`" mode and runs
  only as a dispatched agent.
  - **Evidence:**
    `.agents/plugins/agentdev/agents/iwe-verifier.agent.md#how-you-run › "You run only"`
    and its `description` frontmatter, "Dispatched only by the iwe-verify
    skill"; the "In place inside `iwe-shipper`" mode is gone.

### Task 3: Record the decision

**Files:** Modify: `docs/knowledge/data/architecture/fresh-context-verify.md`,
`docs/knowledge/data/architecture/nested-subagent-dispatch.md`

- [x] The document states that the Shipper dispatches `iwe-verifier` through
  `/agentdev:iwe-verify`, and lists following the rulebook in place as a
  rejected alternative: it puts the whole Verify run in the Shipper's context
  ahead of its graph changes.
  - **Evidence:**
    `docs/knowledge/data/architecture/fresh-context-verify.md#decision › "Every caller takes that route"`
    and
    `docs/knowledge/data/architecture/fresh-context-verify.md#rejected-alternatives › "rulebook in place"`;
    `docs/knowledge/data/architecture/nested-subagent-dispatch.md#host-behavior › "which is why"`
    no longer quotes the Shipper's old tool list.

### Task 4: Ship runs a fresh-context Verify end to end

- [x] `/agentdev:iwe-ship` on a scratch plan with no saved report shows a
  dispatched `iwe-verifier` in the transcript and a saved report afterwards, and
  the catalog validator passes.
  - **Evidence:** the headless run in
    `docs/knowledge/data/architecture/skill-rehearsal-runs.md#running-it`,
    `/agentdev:iwe-ship` on a scratch plan whose `verify-cache.py lookup` is
    `MISS`: the stream holds an `agentdev:iwe-verifier` Agent call whose
    `parent_tool_use_id` is the `agentdev:iwe-shipper` call, and
    `verify-cache.py lookup` on the commit Verify ran on returns `HIT`;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes.

### Task 5: The feature describes the dispatch

**Files:** Modify:
`docs/knowledge/data/features/verification-in-the-main-loop.md`

- [ ] `## Behaviour` states that `iwe-shipper` runs `/agentdev:iwe-verify`,
  which dispatches `iwe-verifier`, so only the report enters the Shipper's
  context, instead of the Shipper following the rulebook in place.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — Ship's Verify step
dispatches `iwe-verifier`.

``` markdown
## MODIFIED Requirements

### Requirement: Normal shipping requires a clean independent verification

The Ship skill SHALL run the report-only Verify workflow before normal shipping
state changes and SHALL refuse to ship while Verify reports any CRITICAL
finding. Verify SHALL remain independently invocable and SHALL not edit code or
project state. Verify's rulebook SHALL be defined once, as the catalog agent
`iwe-verifier`, and every Verify run SHALL start from a fresh context:
`/agentdev:iwe-verify` SHALL dispatch `iwe-verifier` with a prompt carrying only
the plan key or audit mode and the approvals quoted verbatim, whether the user's
session or `iwe-shipper` invokes it. Verify SHALL run a verification command
whose effects reach beyond the working tree only under a quoted approval that
names it, and otherwise SHALL stop before it and report the approval it needs.

`/agentdev:iwe-verify` SHALL refuse to run on a dirty worktree, SHALL save each
report whose verdict is `Ready to ship`, `Blocked`, or `Audit` as the one saved
report for its plan or for audit mode, keyed by the commit it ran on and the
digest of the active agentdev catalog, and SHALL never save a `Needs decision`
report. It SHALL return the saved report, marked as saved and without running
any check or verification command, when that report's commit is `HEAD` and its
catalog digest is the active catalog's, unless the user's request carries
`--fresh`. The saved report SHALL record the request `/agentdev:iwe-verify` was
invoked with and the prompt `iwe-verifier` was dispatched with, and neither
SHALL be part of the key. A verification command that leaves the worktree dirty
SHALL be a CRITICAL finding.

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

#### Scenario: Ship dispatches Verify

- **WHEN** `iwe-shipper` reaches its Verify step and no saved report matches
- **THEN** it runs `/agentdev:iwe-verify`, which dispatches `iwe-verifier` with
  the plan key and the approvals the Shipper's prompt quotes, and only the
  report returns to the Shipper

#### Scenario: Ship reuses the Implement loop's report

- **WHEN** the Implement loop's Verify saved a report for the plan and
  `iwe-shipper` reaches its Verify step on the same clean commit with the same
  active catalog
- **THEN** the skill returns the saved report, marked as saved from that commit,
  without running any check or verification command, and Ship proceeds on its
  verdict

#### Scenario: The commit or the catalog changed

- **WHEN** `HEAD` or the active catalog digest differs from the saved report's
- **THEN** Verify runs in full and its report replaces the saved one

#### Scenario: The worktree is dirty

- **WHEN** `/agentdev:iwe-verify` is invoked with a tracked change or an
  untracked file Git does not ignore
- **THEN** it stops before any Verify step and reports the dirty worktree

#### Scenario: A report that needs a decision is not saved

- **WHEN** Verify reports `Needs decision` and the user re-runs it granting the
  approval
- **THEN** Verify runs again rather than returning the earlier report

#### Scenario: The user asks for a fresh run

- **WHEN** the user runs `/agentdev:iwe-verify <plan> --fresh` on a commit with
  a saved report
- **THEN** Verify runs in full and its report replaces the saved one

#### Scenario: The saved report records how Verify was invoked

- **WHEN** Verify saves a report
- **THEN** its frontmatter carries the request the skill was invoked with and
  the verifier prompt, verbatim, including every approval the prompt quotes

#### Scenario: A verification command dirties the worktree

- **WHEN** a `## Verification` command leaves a tracked change or an unignored
  file behind
- **THEN** Verify reports a CRITICAL naming the dirty paths
```

## Depends on

- [Nest agent dispatch to depth 5 on both
  harnesses](20261103-nested-dispatch-depth.md)

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude`
- `/agentdev:iwe-ship` on a scratch plan with no saved report: the transcript
  shows `iwe-shipper` dispatching `iwe-verifier`, and `verify-cache.py lookup`
  returns `HIT` afterwards.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Any other change to `iwe-shipper`, such as its fix operation: [Review every
  ship against Ship's obligations](20261103-ship-review.md).
- The Implement loop's rule that no agent it dispatches dispatches another.

## Key references

- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md › "tools: Bash, Read, Edit, Write, Grep, Glob, Skill"`
  — `tools:`;
  `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps › "Run Verify for normal shipping.** Invoke the report-only"`
  — step 3, Run Verify for normal shipping
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md#from-a-session` —
  `## From a session`, the one route
- `.agents/plugins/agentdev/agents/iwe-verifier.agent.md#how-you-run` —
  `## How you run`
- `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-normal-shipping-requires-a-clean-independent-verification`
  — Requirement: Normal shipping requires a clean independent verification
- `docs/knowledge/data/architecture/fresh-context-verify.md#decision` —
  `## Decision`
- `docs/knowledge/data/architecture/nested-subagent-dispatch.md#host-behavior` —
  `## Host behavior`, which names the Shipper's tool list
