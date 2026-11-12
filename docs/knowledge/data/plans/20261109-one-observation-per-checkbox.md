---
type: plan
created: 2026-11-09
release:
- bugs/plan-tasks-bundle-independent-observations
description: Each plan checkbox names exactly one observation that closes it, and the planner's coherence check asks that of every checkbox, so an implementer can tick each observation as it arrives.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: docs/knowledge/data/spec/plan-checkbox-evidence.md
rank: 100
---

# One observation per plan checkbox

## Context

[Plan tasks bundle independent
observations](../bugs/plan-tasks-bundle-independent-observations.md): the
planner's granularity rule speaks of tasks, not checkboxes, so one externally
evidenced checkbox can join several separately observed events with "and". The
implementer then cannot tick the observed half and has no place the checkbox
contract names to record it. Step 6's coherence re-read does not ask which
observation closes each checkbox.

## Approach

The rule moves from the task to the checkbox in `iwe-planner`: each checkbox
names exactly one observation that closes it; a checkbox that joins
independently observable events is split, one checkbox per event; an event that
may never occur on its own, such as a failure or cancellation path, names how it
is provoked. Step 6's coherence re-read asks, for every checkbox, which single
observation closes it.

Rejected: extending the Durable Knowledge Auditor's plan scope to flag bundled
checkboxes. That audit looks for durable-knowledge residue; checkbox granularity
is a planning rule the planner owns, and a second gate for it widens the auditor
beyond its one question.

## Implementation Steps

### Task 1: The rule per checkbox

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`

- [x] The `## Rules` bullet "One task is one outcome" also states that each
  checkbox names exactly one observation that closes it, that a checkbox joining
  independently observable events is split into one checkbox per event, and that
  an event that may never occur on its own names how it is provoked.
  - **Evidence:**
    `.agents/plugins/agentdev/agents/iwe-planner.agent.md#rules › "Each checkbox names exactly one observation that closes it"`

### Task 2: The coherence question

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`

- [ ] Step 6 asks, for every checkbox, which single observation closes it, and
  splits any checkbox that names more than one.

## Spec changes

[Plan checkbox evidence](../spec/plan-checkbox-evidence.md):

``` markdown
## MODIFIED Requirements

### Requirement: Plan tasks are sized so a tick can be honest

The Plan skill SHALL constrain task granularity so that one task is one outcome
and one checkbox is one observation. A task that could be described as
half-done SHALL be split, a task whose evidence is external SHALL stand alone,
and a checkbox that joins independently observable events SHALL be split into
one checkbox per event. Plan's coherence check SHALL ask, for every checkbox,
which single observation closes it.

#### Scenario: A task bundles two outcomes

- **WHEN** a planned task could ever be described as half-done
- **THEN** Plan splits it, preventing a tick earned by the half done locally
  from reading as a claim about the half that was not

#### Scenario: A task's evidence is external

- **WHEN** a task's evidence is a CI run, a deploy, a review, or a published
  artifact
- **THEN** it is planned as its own task, because the session writing the code
  cannot close it

#### Scenario: A checkbox joins independent observations

- **WHEN** a checkbox's outcome needs two or more events observed separately,
  such as a passing run and a failing run
- **THEN** Plan splits it into one checkbox per event, so each can be ticked
  with its own evidence as it is observed

#### Scenario: An event may never occur on its own

- **WHEN** a checkbox's observation is a failure or cancellation path that
  normal operation may never produce
- **THEN** the checkbox names how the event is provoked
```

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
- `uv run scripts/check-anchors.py` exits 0.
- `iwe normalize && git diff --exit-code` and `iwe schema validate` pass.

## Out of scope

- The Durable Knowledge Auditor and `iwe-audit`'s plan scope.
- Re-splitting checkboxes in existing plans.
- What an evidence line names — [Plan task evidence without commit
  ids](20261109-evidence-without-commit-ids.md).

## Key references

- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#rules › "One task is one outcome; if the task could ever be described as half-done,"`
  — the granularity rule
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps › "Check coherence."`
  — step 6
- `docs/knowledge/data/spec/plan-checkbox-evidence.md#requirement-plan-tasks-are-sized-so-a-tick-can-be-honest`
  — the modified requirement
