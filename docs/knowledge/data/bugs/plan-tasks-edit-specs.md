---
type: bug
description: Plan accepts implementation tasks that create or edit data/spec/ documents, which only Ship may change, and the plan-scope audit does not flag them.
generated:
  by: claude-code/opus-5
  at: 2026-10-25T06:22:37Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-audit/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: docs/knowledge/data/spec/iwe-workflow-skills.md
---

# Bug: plan tasks edit spec documents that only Ship may change

## Symptom

A plan's `## Implementation Steps` can carry a task whose `**Files:**` line
creates or modifies `data/spec/` documents and whose checkboxes ask the
implementer to write requirements into them. That task duplicates the plan's own
`## Spec changes`, and executing it syncs the durable spec before Verify and
Ship — the spec then describes unshipped behavior, and Ship's merge of the delta
lands on a spec that already changed. The plan-scope audit passes such a task
without comment.

## Reproduction

1. Read
   `git show 1570a99:docs/knowledge/data/plans/20261023-reusable-iwe-bootstrap.md`.
   Its Task 5 lists `Create: docs/knowledge/data/spec/iwe-bootstrap.md` and
   `Modify: docs/knowledge/data/spec/template-consumption.md`,
   `docs/knowledge/data/spec.md`, with checkboxes to "Document the independently
   invokable bootstrap contract" and "Update full-adoption requirements" — the
   same content its `## Spec changes` delta already records for Ship.
2. That plan was filed through `/agentdev:iwe-plan` and passed its step 8
   `iwe normalize` and `iwe schema validate`.
3. Read `/agentdev:iwe-audit`'s plan scope and its §1 smell list: every pattern
   targets residue wording, and none matches a task that targets `data/spec/`,
   so the Durable Knowledge Auditor has nothing to report on it.

## Root cause

`/agentdev:iwe-plan` describes `## Spec changes` as the plan's spec impact and
says the durable spec keeps released behavior until Ship merges it, but its
`## Implementation Steps` instructions and `## Rules` never forbid a task from
editing `data/spec/`. Nothing else catches it: the implementer rulebook says
only that spec sync stays with Ship, without telling the implementer to refuse
such a task, and `/agentdev:iwe-audit` plan scope looks only for
durable-knowledge residue, so a structurally misplaced task is outside every
pattern it checks.

## Fix

Not fixed. The intended outcome: `/agentdev:iwe-plan` states as a rule that no
task creates, modifies, or deletes a `data/spec/` document or the `data/spec`
hub, and that spec impact lives only in `## Spec changes` for Ship to merge; and
the plan-scope audit reports any task whose `**Files:**` line or checkbox text
targets `data/spec/` as a finding that routes back to `/agentdev:iwe-plan`
revise mode.

## Key references

Verified anchor points (line numbers as of 2026-10-25):

- `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md:69` —
  `## Implementation Steps` authoring instructions, with no spec-document
  exclusion
- `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md:212` — `## Rules`, which
  never forbid a task from editing `data/spec/`
- `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md:41` — plan scope, limited
  to residue patterns
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:157` — "spec sync
  ... stay with the `/agentdev:iwe-ship` skill", with no instruction for a task
  that asks for it
- `docs/knowledge/data/spec/iwe-workflow-skills.md:350` — Requirement: Ship
  synchronizes durable specs by intelligent merge
