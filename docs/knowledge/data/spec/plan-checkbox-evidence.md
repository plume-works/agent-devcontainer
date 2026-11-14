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

Evidence has one purpose: to stop a box being ticked for work that was not done,
where a blanket substitution and a set of careful verifications produce
identical bytes and only the evidence line tells them apart. Nothing else reads
it: the `plan-checkboxes` gate checking the note is present is the only check on
a tick, and Verify never checks ticks or their notes.

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
