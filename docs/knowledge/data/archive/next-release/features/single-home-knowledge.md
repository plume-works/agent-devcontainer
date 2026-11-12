---
type: feature
stage: implemented
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
- A feature is a proposal. Ship archives it with the plan that implements it.
- Whoever closes a plan, bug, task, or feature moves it to
  `data/archive/next-release/<type>/` and removes its hub link. Ship first
  writes the plan's lasting decision into the owning spec's `## Rationale`.
- A release cut moves `data/archive/next-release/` into
  `data/archive/<version>/`. The folder is the only record of a document's
  release.
- A release cut writes the release page from the difference in `data/spec/`
  since the previous cut: what changed, in plain language, with no link, and the
  titles of the bugs the release closed.
- Archived documents pass the schema of their type.
- There is no `data/log.md`.

## Edge cases

- A document closed by no plan belongs to the release open when it closed.
- A live plan and an archived plan with the same slug are ambiguous to
  `/agentdev:iwe-branch-name`.
- A change the spec difference does not explain, and no archived plan of the
  release settles, is reported by the cut and left off the page.
- A repository that consumed the earlier scaffold keeps its layout until it is
  migrated.

## Open questions

None.
