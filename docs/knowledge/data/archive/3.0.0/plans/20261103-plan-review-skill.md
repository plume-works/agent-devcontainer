---
type: plan
created: 2026-11-03
release:
- features/ship-review
description: Add the iwe-plan-review skill, which dispatches the Durable Knowledge Auditor and iwe-ship-reviewer in plan mode on one plan and returns both reports, and have iwe-planner step 7 run it on every plan edit.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/agents/durable-knowledge-auditor.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
stage: done
completed: 2026-11-12
---

# The iwe-plan-review skill

## Context

[Ship review](../features/ship-review.md) gives `iwe-ship-reviewer` a plan mode
that reports whether a plan gives Ship what it needs. The repository owner
decided that a new skill, `/agentdev:iwe-plan-review`, runs it alongside the
`Durable Knowledge Auditor` agent on every plan edit.

## Approach

`/agentdev:iwe-plan-review <plan>` dispatches, in parallel, the
`Durable Knowledge Auditor` agent with the plan file and plan scope, and
`iwe-ship-reviewer` in plan mode with the plan key. Each prompt carries nothing
else. It returns both reports together and changes nothing. The skill is
model-invocable so `iwe-planner` can run it.

`iwe-planner` step 7 runs `/agentdev:iwe-plan-review` in place of its direct
`Durable Knowledge Auditor` dispatch. It applies the auditor's report-only
verdicts to the draft, and fixes the plan for each `iwe-ship-reviewer` finding,
asking the user where a fix is a material choice. Every mode of the rulebook
runs it, so the Implement session's revisions are reviewed the same way.

Rejected: widening the `Durable Knowledge Auditor` agent's rubric to Ship's
obligations. `iwe-ship-reviewer` has to exist for its ship mode anyway, and one
rubric in two agents would drift.

## Implementation Steps

### Task 1: The fan-out skill

**Files:** Create: `.agents/plugins/agentdev/skills/iwe-plan-review/SKILL.md`;
Modify: `.agents/plugins/agentdev/README.md`,
`.agents/plugins/agentdev/agents/iwe-ship-reviewer.agent.md`

- [x] The skill dispatches both agents in parallel with prompts carrying only
  the plan file and scope, or the plan key and plan mode, and returns both
  reports unchanged.
  - **Evidence:**
    `.agents/plugins/agentdev/skills/iwe-plan-review/SKILL.md#steps`; the
    skill's row in
    `.agents/plugins/agentdev/README.md#knowledge-graph-workflow-iwe` and the
    `iwe-ship-reviewer` frontmatter `description` naming it as a dispatcher;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes.

### Task 2: Plan runs the review

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`,
`.agents/plugins/agentdev/agents/iwe-implementer.agent.md`

- [x] Step 7 runs `/agentdev:iwe-plan-review`, applies the auditor's verdicts,
  and resolves each `iwe-ship-reviewer` finding before step 8.
  - **Evidence:**
    `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps › "Review the plan from a fresh context.** In both create and"`;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    passes.
- [x] `iwe-implementer`'s revision step names the review in place of the
  `Durable Knowledge Auditor` gate.
  - **Evidence:**
    `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#running-the-loop › "its `/agentdev:iwe-plan-review` gate and validation, and leave"`.

### Task 3: A plan edit runs both reviewers

**Closed by:** the user, or a session the user directs, running
`/agentdev:iwe-plan` headless (`claude -p --plugin-dir`) against this branch's
catalog in a scratch worktree.

- [x] `/agentdev:iwe-plan` creating a scratch plan whose `release` lists a
  pending bug shows both agents dispatched in the transcript, and the plan ends
  with that bug at `stage: planned`.
  - **Evidence:** observed 2026-11-12 by a session the user directed, in a
    scratch worktree of this branch at a5dfe5f5, run from its root:
    `claude -p --plugin-dir "$PWD/.agents/plugins/agentdev" --permission-mode acceptEdits --output-format stream-json --verbose "/agentdev:iwe-plan Create a plan that fixes the bug data/bugs/self-improve-unstageable-routing-option. Its release lists that bug. Decisions, already made so you need not ask: create mode; leave the plan unsequenced (no rank); choose the simplest fix you find and record it as an assumption; do not commit. This is a non-interactive run: where a step would ask the user, make the reasonable assumption, record it in the plan, and continue."`.
    The transcript shows `agentdev:iwe-plan-review` dispatching
    `agentdev:Durable Knowledge Auditor` with the plan file and `scope: plan`
    and `agentdev:iwe-ship-reviewer` with the plan key and `mode: plan` in one
    message; `data/bugs/self-improve-unstageable-routing-option` ended at
    `stage: planned`.

## Spec changes

[IWE workflow skills](../../../spec/iwe-workflow-skills.md) — every plan edit
gets both reviews, and the Implement loop allows that dispatch.

``` markdown
## MODIFIED Requirements

### Requirement: Plans record intent, not the path taken to it

Plan documents SHALL record what is settled rather than the sequence of attempts
that settled it. `## Verification results` SHALL be a plan's only narrative
section. Implement SHALL route a finding that does not change the plan's intent
to its own document — `data/architecture/`, `data/bugs/`, or `data/backlog/` —
rather than into the plan's `## Context` or `## Approach`, which state intent
and remain the Plan skill's to own. Every edit to a plan's intent sections SHALL
be reviewed through `/agentdev:iwe-plan-review` before the edit is validated:
audited for durable-knowledge residue by a reviewer holding no context beyond
the audit scope and the plan file, and checked by `iwe-ship-reviewer` in plan
mode for what Ship will need.

#### Scenario: Implementation produces a durable finding

- **WHEN** implementation establishes a constraint, root cause, or rejected
  alternative that the plan did not anticipate
- **THEN** Implement records it in the reference document that owns the area and
  reports the capture, leaving the plan's intent sections unchanged

#### Scenario: A session narrates its attempts into a plan

- **WHEN** a plan would gain a running account of an in-flight investigation —
  failed attempts, CI run identifiers, per-attempt tables
- **THEN** that content is excluded from the plan, because it would not be true
  had the work succeeded the first time

#### Scenario: A finding changes the plan's intent

- **WHEN** a finding alters scope, observable behavior, compatibility,
  acceptance criteria, dependencies, or an out-of-scope boundary
- **THEN** it goes back through the Plan skill's revise mode rather than being
  captured elsewhere or written into the plan directly

#### Scenario: A plan edit is audited before validation

- **WHEN** Plan creates or revises a plan and reaches validation
- **THEN** a reviewer holding only the audit scope and the plan file audits its
  intent sections for durable-knowledge residue, its verdicts are applied, and
  the narrative-sanctioned `## Verification results` and `- **Evidence:**`
  children are left out of that audit

#### Scenario: A plan edit is checked for what Ship needs

- **WHEN** Plan creates or revises a plan and reaches validation
- **THEN** `iwe-ship-reviewer` in plan mode reports whether the plan gives Ship
  what it needs, and Plan resolves each finding before validating

### Requirement: Implement verifies its own work and acts on the report

When a plan's last task closes, the Implement session — the session that loaded
`/agentdev:iwe-implement` — SHALL run Verify through `/agentdev:iwe-verify` and
SHALL act on every CRITICAL finding, and on a WARNING only when its fix fits a
task the plan already has and adds no claim the code must newly meet. It SHALL
file every other WARNING through `/agentdev:iwe-capture`, report SUGGESTIONs
only, and SHALL not stop for an outstanding observation. A code or evidence
finding SHALL be fixed under the Implement rules and verified again, and a
finding about the plan's intent SHALL go through an evaluated revision. The
Implement session SHALL stop when a finding recurs after a fix attempt, after
three Verify rounds, or after one approved revision in the run. No agent the
loop dispatches SHALL dispatch another; while a revision is drafted, the loop
may also dispatch the two agents `/agentdev:iwe-plan-review` names.

#### Scenario: Verify finds nothing to act on

- **WHEN** the plan's tasks are closed and Verify reports zero CRITICAL findings
  and no WARNING whose fix fits an existing task
- **THEN** the run ends with its rollup and the Verify verdict, and suggests
  `/agentdev:iwe-ship`

#### Scenario: Verify finds a code defect

- **WHEN** the Verify report carries a CRITICAL whose route is code or evidence
- **THEN** the Implement session fixes it under the Implement rules, closes it
  with evidence, and runs Verify again through `/agentdev:iwe-verify`

#### Scenario: A warning would add work

- **WHEN** Verify reports a WARNING whose fix needs a new task or a new claim
- **THEN** the Implement session files it through `/agentdev:iwe-capture`, names
  it in the report, and does not act on it in this run

#### Scenario: An observation is outstanding

- **WHEN** Verify lists an unticked `**Closed by:**` task under Outstanding
  observations and reports nothing else to act on
- **THEN** the run ends with its rollup naming the observation

#### Scenario: A finding recurs

- **WHEN** a finding the Implement session already tried to fix appears in the
  next Verify report
- **THEN** the run stops and reports the finding, the fix it attempted, and the
  Verify report

#### Scenario: Verify needs an approval

- **WHEN** Verify reports `Needs decision` for a command with effects beyond the
  working tree
- **THEN** the run stops and names the approval, which the user grants by
  re-running the skill
```

## Depends on

- [Review every ship against Ship's obligations](20261103-ship-review.md)
- [Nest agent dispatch to depth 5 on both
  harnesses](20261103-nested-dispatch-depth.md)

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude`
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Refactoring `/agentdev:iwe-audit` and the `Durable Knowledge Auditor` agent so
  the agent holds the rulebook, or renaming the agent: `/agentdev:iwe-audit`
  edits the audited file after approval in its default scope, and where that
  edit lives is not settled.
- `/agentdev:pr-review`'s use of `/agentdev:iwe-audit`.

## Key references

- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps › "Review the plan from a fresh context.** In both create and"`
  — step 7, Review the plan from a fresh context
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#running-the-loop › "its `/agentdev:iwe-plan-review` gate and validation, and leave"`
  — the revision step's review gate
- `.agents/plugins/agentdev/agents/durable-knowledge-auditor.agent.md › "tools: Bash, Read, Grep, Glob, Skill"`
  — `tools:`
- `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-implement-verifies-its-own-work-and-acts-on-the-report`
  — Requirement: Implement verifies its own work and acts on the report;
  `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-plans-record-intent-not-the-path-taken-to-it`
  — Requirement: Plans record intent, not the path taken to it

## Ship review

Reviewed by `iwe-ship-reviewer` on 2026-11-12.

- [x] Verify reported zero CRITICAL — confirmed: Ready to ship:
  data/plans/20261103-plan-review-skill
- [x] Every `## Spec changes` operation is in its spec — confirmed:
  data/spec/iwe-workflow-skills
- [x] Every spec the plan created is linked from `data/spec.md` — N/A: no spec
  created
- [x] Every spec the plan retired was removed with `iwe delete` — N/A: no spec
  retired
- [x] The plan is `stage: done` with `completed` and no `rank` — confirmed:
  2026-11-12
- [x] Every feature in `release` is `stage: implemented` — confirmed:
  data/features/ship-review
- [x] Every bug in `release` is `stage: done` with no `rank` — N/A: `release`
  lists no bug
- [x] Every bug in `release` has a `## Fix` that links this plan — N/A:
  `release` lists no bug
- [x] Ship edited no hub, release page, or `data/log.md` — confirmed
