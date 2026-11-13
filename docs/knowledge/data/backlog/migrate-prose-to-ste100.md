---
type: task
stage: pending
priority: low
created: 2026-11-12
description: Convert the prose written before the ASD-STE100 rule to ASD-STE100, and prove with the semantic-refactor audit that each rewrite keeps its meaning.
sources:
- resource: https://www.asd-ste100.org/
- resource: .agents/plugins/agentdev/skills/semantic-refactor-audit/SKILL.md
- resource: docs/knowledge/data/backlog/shrink-knowledge-base-to-issues-and-adrs.md
---

# Migrate existing prose to ASD-STE100

The repository owner decided on 2026-11-12 that ASD-STE100 is a hard rule for
all prose the agents write. The rule applies only to text that a change adds or
edits. Text written before the rule stays as it is, so one document can hold
both styles. This task converts the earlier text.

## Scope

The rule, and this task, cover:

- every document under `docs/knowledge/data/`;
- `docs/knowledge/AGENTS.md`, `docs/knowledge/SCHEMA.md`,
  `docs/knowledge/STRUCTURE.md`, and the copies that the `iwe-bootstrap` skill
  installs;
- the skill and agent rulebooks under `.agents/plugins/`;
- the root `AGENTS.md` and the READMEs.

## Decisions

Each decision is the repository owner's.

- The migration is a separate task. It is not part of the plan that introduces
  the rule.
- `/agentdev:semantic-refactor-audit` proves that each rewrite keeps the meaning
  of the text it replaces.

## Order

This task starts after the plan that introduces the rule ships. That plan adds
the `audit-ste100` skill and `docs/knowledge/data/glossary.md`, which is the
ASD-STE100 list of technical names for this project.
