---
type: feature
stage: implemented
description: The IWE workflow skills are part of the agentdev catalog as iwe-prefixed, plugin-portable skills rather than repository-local Claude skills.
generated:
  by: claude-code/opus-5.5
  at: 2026-09-27T09:53:38Z
sources:
- resource: docs/knowledge/data/plans/20260816-move-iwe-skills-to-agentdev.md
- resource: docs/knowledge/data/spec/template-consumption.md
- resource: docs/knowledge/data/spec/iwe-workflow-skills.md
- resource: .agents/plugins/agentdev/skills/iwe-explore/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-capture/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-ship/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-setup/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-map/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-weekly/SKILL.md
---

# Agentdev IWE workflow skills

## Purpose

The IWE workflow belongs to the `agentdev` catalog, so consuming projects
receive the skills through the installed plugin instead of inheriting hidden
repository-local Claude skills from `.claude/`.

## Behaviour

**The nine workflow skills live in the plugin.** Setup, Map, Explore, Plan,
Capture, Implement, Verify, Ship, and Weekly are shipped from
`.agents/plugins/agentdev/skills/iwe-*/` and invoked as `/agentdev:iwe-*`.

**Map owns the `data/codebase/` lane.** Setup defers the per-module map to Map's
initial mode, and Verify's audit hands stale map docs to Map's refresh mode, so
every `data/` lane has exactly one writer.

**Capture owns the inbox lanes.** Explore and Implement hand settled bugs,
proposed features, and backlog tasks to Capture rather than writing them, so
`data/bugs/`, `data/features/` at `proposed`, and `data/backlog/` have one
writer and one enforced shape.

**Skill-to-skill references are plugin-portable.** The workflow instructions use
namespaced `/agentdev:iwe-*` invocations for sibling handoffs, so the catalog
does not rely on repository-relative `.claude/skills/` paths.

**The template copy surface stays explicit.** `.claude/` remains project-facing
configuration, while the workflow skills travel with the installed `agentdev`
catalog described by the devcontainer lifecycle.

## Edge cases

- **A consuming project attaches.** The skills resolve from the installed
  `agentdev` catalog; the consumer has no `.claude/skills/` copy to fall back
  on, so a skill missing from the catalog does not resolve at all.
- **This repository edits a skill.** The checkout's own
  `.agents/plugins/agentdev/` is re-registered over the staged catalog on
  attach, so the edited skill is the one invoked.
- **Setup runs on a workspace with code.** Setup does not write `data/codebase/`
  itself; it hands the per-module map to Map's initial mode.

## Open questions

None — every design question this feature raised is settled.

## References

- Plan: [Move the IWE workflow skills into the agentdev
  plugin](../plans/20260816-move-iwe-skills-to-agentdev.md)
- Specs: [Template consumption](../spec/template-consumption.md) and [IWE
  workflow skills](../spec/iwe-workflow-skills.md)
