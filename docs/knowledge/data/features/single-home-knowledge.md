---
type: feature
stage: accepted
description: Each kind of project knowledge has one home in the graph — behaviour and its rationale in specs, findings and guides in their own types — and finished work moves to a per-release archive.
sources:
- resource: docs/knowledge/AGENTS.md
- resource: docs/knowledge/SCHEMA.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
---

# One home for each kind of knowledge

## Purpose

A reader of the knowledge graph finds each fact in one place. Behaviour is in a
spec, the reason for it sits beside it, and finished work is out of the way
without a link breaking.

## Behaviour

- Behaviour is stated only in `data/spec/` requirements.
- The decision in force and the alternatives it rejected are in the
  `## Rationale` section of the spec that owns the behaviour.
- A finding is a `data/findings/` document, and a procedure is a `data/guides/`
  document. There is no architecture type.
- A feature describes behaviour in prose until it is implemented; from then on
  its `## Behaviour` links the spec requirements that own it.
- Whoever closes a plan, bug, or task moves it to
  `data/archive/next-release/<type>/` and removes its hub link. Ship first
  writes the plan's lasting decision into the owning spec's `## Rationale`.
- A release cut moves `data/archive/next-release/` into
  `data/archive/<version>/`. The folder is the only record of a document's
  release.
- Archived documents pass the schema of their type.

## Edge cases

- A document closed by no plan belongs to the release open when it closed.
- A live plan and an archived plan with the same slug are ambiguous to
  `/agentdev:iwe-branch-name`.
- A repository that consumed the earlier scaffold keeps its layout until it is
  migrated.

## Open questions

None.
