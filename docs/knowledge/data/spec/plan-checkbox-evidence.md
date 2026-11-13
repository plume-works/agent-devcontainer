---
type: spec
description: A ticked plan checkbox carries a free-form evidence note so a box is never ticked for work that was not done, tasks are atomic, and a mechanical gate checking the note is present is the only check on ticks; Verify never checks them.
sources:
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: docs/knowledge/tests/test_plan_checkboxes.py
- resource: py_packages/validate_agent_files/README.md
- resource: docs/knowledge/AGENTS.md
---

# Plan checkbox evidence

## Purpose

A plan document is the record the next session builds on, and its checkboxes are
its most load-bearing claim. This specifies what a tick must carry, how tasks
must be sized so a tick can be honest, and the gate that checks a tick carries
its note.

Evidence has one purpose: to stop a box being ticked for work that was not
done, where a blanket substitution and a set of careful verifications produce
identical bytes and only the evidence line tells them apart. Nothing else reads
it: the `plan-checkboxes` gate checking the note is present is the only check on
a tick, and Verify never checks ticks or their notes.

## Requirements

### Requirement: A ticked task carries the evidence that closed it

Every ticked `- [x]` task under a plan's task section SHALL carry an indented
`- **Evidence:**` child: a short free-form note of what was done and how it was
checked, in any form — a test, a command, a file, a manual or live check, a CI
run, a PR, or a commit. No form of the note SHALL be preferred, required, or
rejected. Implement SHALL write the evidence line in the same edit that ticks
the box and commit it together with the change it describes, and the convention
SHALL be recorded where every session loads it rather than only where a skill is
invoked.

#### Scenario: A task is completed

- **WHEN** a task's complete specified behavior is implemented and its required
  tests and checks pass
- **THEN** one edit ticks the box and writes its `- **Evidence:**` child noting
  what was done

#### Scenario: Work is partial or its checks fail

- **WHEN** a task is only partially implemented, contains deferred behavior, or
  its required tests or checks do not pass
- **THEN** the box stays unticked and carries no evidence line

#### Scenario: Several boxes would be ticked at once

- **WHEN** more than one checkbox would change state
- **THEN** each is a separate edit, because a blanket `- [ ]` → `- [x]`
  substitution is itself the defect

### Requirement: Plan tasks are sized so a tick can be honest

The Plan skill SHALL constrain task granularity so that one task is one outcome
and one checkbox is one observation. A task that could be described as half-done
SHALL be split, a task whose evidence is external SHALL stand alone, and a
checkbox that joins independently observable events SHALL be split into one
checkbox per event. Plan's coherence check SHALL ask, for every checkbox, which
single observation closes it.

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

### Requirement: Plans record narrative verification evidence

A plan SHALL have a specified home for evidence about the work as a whole:
`## Verification results`, following `## Verification`, written as the work
happens rather than reconstructed at the end, and omitted until there is
something to record.

#### Scenario: A plan accumulates verification evidence

- **WHEN** a session runs a plan's verification commands or discovers something
  that changes what the plan claims
- **THEN** it records the result under `## Verification results` rather than
  improvising a section per plan

### Requirement: Verify never checks ticked tasks or their evidence

The `plan-checkboxes` gate SHALL be the only check on a ticked task and its
`- **Evidence:**` note. Verify SHALL report no finding of any severity about a
ticked task or its note, and SHALL NOT re-run, re-observe, or seek approval to
repeat a test, command, or live check the note records. An unticked task with no
`**Closed by:**` line SHALL remain a CRITICAL.

#### Scenario: The evidence note records a live or manual check

- **WHEN** a ticked task's evidence note records a check Verify cannot or would
  need approval to repeat, such as a live session or a deploy
- **THEN** Verify neither re-runs it nor stops for a decision about it

#### Scenario: The evidence note has any form

- **WHEN** a ticked task's evidence note names only a commit, only a code
  anchor, raw output, or prose
- **THEN** Verify reports nothing about it

#### Scenario: A task is left unticked

- **WHEN** an unticked `- [ ]` task carries no `**Closed by:**` line
- **THEN** Verify reports a CRITICAL naming three routes out — complete the
  task, tick it if it is already done, or drop it through Plan's revise mode,
  which treats dropping a task as a material scope change and asks the user —
  and takes none of them

### Requirement: The checkbox format is mechanically gated

A test SHALL audit every plan document and report every violation with
`path:line`, not only the first. It SHALL run from the repository's test suite,
from a pre-commit hook when a plan changes, and in the knowledge-base CI job.

#### Scenario: An active plan has an unsupported tick

- **WHEN** a plan with no `stage` in frontmatter has a ticked task whose
  indented `- **Evidence:**` child is absent or empty
- **THEN** the gate fails and names the offending `path:line`

#### Scenario: A completed plan still has open work

- **WHEN** a plan carries `stage: done` and any task is still `- [ ]`
- **THEN** the gate fails and names the offending `path:line`

#### Scenario: A closed plan lacks evidence lines

- **WHEN** a plan carries `stage: done` and its ticked tasks have no evidence
  children
- **THEN** the gate passes, because closed plans are historical records and
  backfilling evidence into them would be inventing it

#### Scenario: A plan uses the older task heading

- **WHEN** a plan heads its checkboxes `## Tasks` rather than
  `## Implementation Steps`
- **THEN** the gate audits it, because silently skipping a whole document is the
  invisibility this contract exists to remove

#### Scenario: A checkbox appears outside the task section

- **WHEN** a checkbox appears under another section, such as a format example
  under `## Approach`, or inside a fenced code block
- **THEN** the gate does not treat it as a task

## Rationale

### Evidence is a free-form note the gate alone checks

A ticked task's evidence is a short note in any form, and Verify never reads it.
The note exists only so a box is never ticked without a claim beside it; that is
a shape the `plan-checkboxes` gate holds on every commit. Grading the note's
form or re-running what it names made Verify stop on checks it could not repeat
in its checkout — a live session, a deploy, a person — and report findings
against plans whose code conformed. A task's code, its tick, and its evidence
line land in one commit.

Rejected:

- **Evidence that names a check Verify repeats.** Live, manual, and external
  checks have nothing Verify can re-run, so the rule either blocks Verify or
  pushes such work out of plans.
- **Rejecting commit ids or raw output.** The note's only reader is the gate,
  which needs a claim, not a particular form.

### Honest ticks come from the artifact's shape, not more prose rules

A tick is honest only when it carries an evidence line, because rules telling
Implement when it may tick were already written and were violated anyway. A
find-and-replace can flip every box in a file; it cannot write the evidence line
each tick needs.

Rejected:

- **Another round of prose rules in the Implement rulebook.** The rules that
  would have prevented over-claiming already existed; more of the same changes
  nothing a sweep can bypass.

### The gate is a knowledge-base test, not a validator extension

The checkbox gate is `docs/knowledge/tests/test_plan_checkboxes.py`, run by
pytest, because plan documents are this workspace's knowledge graph, not agent
files.

Rejected:

- **Extending `validate_agent_files`.** That package validates skills, agents,
  and prompts in any repository and must stay usable with no knowledge of this
  one's graph.

### Checkbox granularity is the planner's rule

One observation per checkbox is a planning rule, so `iwe-planner` owns it.

Rejected:

- **The Durable Knowledge Auditor flags bundled checkboxes in its plan scope.**
  That audit asks one question, durable-knowledge residue, and a second gate
  would widen it.
