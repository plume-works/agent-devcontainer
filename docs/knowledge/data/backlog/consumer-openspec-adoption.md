---
type: task
stage: pending
priority: medium
created: 2026-11-10
description: Decide how a consuming repository adopts OpenSpec for its specs, then update the iwe-bootstrap scaffold and template-consume guidance, which still ship spec and architecture hubs no IWE skill maintains.
sources:
- resource: openspec/changes/specs-sole-source-of-truth/design.md
- resource: .agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
---

# Give consumers OpenSpec in place of the scaffold's spec and architecture hubs

This repository's graph no longer holds specs or architecture notes: behavior
and its rationale live in `openspec/specs/`, measurements in `data/findings/`,
and no IWE skill writes a spec. The `iwe-bootstrap` scaffold a consumer receives
still carries `data/spec.md`, `data/architecture.md`, their folders, their
schemas, and their bindings, and its `AGENTS.md`, `SCHEMA.md`, and
`STRUCTURE.md` still describe spec sync at ship. `template-consume` still adopts
that shape. A bootstrapped consumer therefore gets hubs nothing maintains.

Decide how a consumer adopts OpenSpec — whether bootstrap or template-consume
runs `openspec init`, and what happens to a consumer's existing `data/spec/` and
`data/architecture/` documents — then bring the scaffold, its schemas and
support documents, and the consumption guide in line with [Project
knowledge](../../../../openspec/specs/project-knowledge/spec.md).
