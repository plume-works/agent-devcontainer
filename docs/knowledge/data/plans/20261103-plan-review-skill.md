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
---

# The iwe-plan-review skill

## Context

[Ship review](../features/ship-review.md) gives `iwe-ship-reviewer` a plan mode
that reports whether a plan gives Ship what it needs. The repository owner
decided that a new skill, `/agentdev:iwe-plan-review`, runs it alongside the
`Durable Knowledge Auditor` agent on every plan edit. Today step 7 of
`iwe-planner.agent.md` dispatches only the `Durable Knowledge Auditor` agent.

## Approach

`/agentdev:iwe-plan-review <plan>` dispatches, in parallel, the
`Durable Knowledge Auditor` agent with the plan file and plan scope, and
`iwe-ship-reviewer` in plan mode with the plan key. Each prompt carries nothing
else. It returns both reports together and changes nothing. The skill is
model-invocable so `iwe-planner` can run it.

`iwe-planner` step 7 runs `/agentdev:iwe-plan-review` in place of its direct
`Durable Knowledge Auditor` dispatch. It applies the auditor's verdicts as
today, and fixes the plan for each `iwe-ship-reviewer` finding, asking the user
where a fix is a material choice. Every mode of the rulebook runs it, so the
Implement session's revisions are reviewed the same way.

Rejected: widening the `Durable Knowledge Auditor` agent's rubric to Ship's
obligations. `iwe-ship-reviewer` has to exist for its ship mode anyway, and one
rubric in two agents would drift.

## Implementation Steps

### Task 1: The fan-out skill

**Files:** Create: `.agents/plugins/agentdev/skills/iwe-plan-review/SKILL.md`

- [ ] The skill dispatches both agents in parallel with prompts carrying only
  the plan file and scope, or the plan key and plan mode, and returns both
  reports unchanged.

### Task 2: Plan runs the review

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`,
`.agents/plugins/agentdev/agents/iwe-implementer.agent.md`

- [ ] Step 7 runs `/agentdev:iwe-plan-review`, applies the auditor's verdicts,
  and resolves each `iwe-ship-reviewer` finding before step 8.
- [ ] `iwe-implementer`'s revision step names the review in place of the
  `Durable Knowledge Auditor` gate.

### Task 3: A plan edit runs both reviewers

- [ ] `/agentdev:iwe-plan` creating a scratch plan whose `release` lists a
  pending bug shows both agents dispatched in the transcript, and the plan ends
  with that bug at `stage: planned`.

## Spec changes

[IWE workflow skills](../../../../openspec/specs/iwe-workflow-skills/spec.md) —
every plan edit gets both reviews, and the Implement loop allows that dispatch.

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
`/agentdev:iwe-implement` — SHALL run Verify through `/agentdev:iwe-verify` and SHALL act on
every CRITICAL finding and every WARNING that names a concrete route, reporting
SUGGESTIONs only. A code or evidence finding SHALL be fixed under the Implement
rules and verified again, and a finding about the plan's intent SHALL go through
an evaluated revision. The Implement session SHALL stop when a finding recurs after a
fix attempt, after three Verify rounds, or after one approved revision in the
run. No agent the loop dispatches SHALL dispatch another, except the two
agents `/agentdev:iwe-plan-review` dispatches while a revision is drafted.

#### Scenario: Verify finds nothing to act on

- **WHEN** the plan's tasks are closed and Verify reports zero CRITICAL findings
  and no WARNING with a concrete route
- **THEN** the run ends with its rollup and the Verify verdict, and suggests
  `/agentdev:iwe-ship`

#### Scenario: Verify finds a code defect

- **WHEN** the Verify report carries a CRITICAL whose route is code or evidence
- **THEN** the Implement session fixes it under the Implement rules, closes it
  with evidence, and runs Verify again through `/agentdev:iwe-verify`

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
- The Task 3 run on a scratch plan.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Refactoring `/agentdev:iwe-audit` and the `Durable Knowledge Auditor` agent so
  the agent holds the rulebook, or renaming the agent: `/agentdev:iwe-audit`
  edits the audited file after approval in its default scope, and where that
  edit lives is not settled.
- `/agentdev:pr-review`'s use of `/agentdev:iwe-audit`.

## Key references

- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps › "Audit the plan from a fresh context.** In both create and"`
  — step 7, Audit the plan from a fresh context
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#running-the-loop › "its Durable Knowledge Auditor gate and validation, and leave"`
  — the revision step's Durable Knowledge Auditor gate
- `.agents/plugins/agentdev/agents/durable-knowledge-auditor.agent.md › "tools: Bash, Read, Grep, Glob, Skill"`
  — `tools:`
- `openspec/specs/iwe-workflow-skills/spec.md#requirement-implement-verifies-its-own-work-and-acts-on-the-report`
  — Requirement: Implement verifies its own work and acts on the report;
  `openspec/specs/iwe-workflow-skills/spec.md#requirement-plans-record-intent-not-the-path-taken-to-it`
  — Requirement: Plans record intent, not the path taken to it
