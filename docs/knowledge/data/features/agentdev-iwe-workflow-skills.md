---
type: feature
stage: implemented
description: The IWE workflow skills are part of the agentdev catalog as iwe-prefixed, plugin-portable skills rather than repository-local Claude skills.
generated:
  by: codex/gpt-5
  at: 2026-09-02T05:54:56Z
sources:
- resource: docs/knowledge/data/plans/20260816-move-iwe-skills-to-agentdev.md
- resource: docs/knowledge/data/spec/template-consumption.md
- resource: docs/knowledge/data/spec/iwe-workflow-skills.md
- resource: .agents/plugins/agentdev/skills/iwe-explore/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-ship/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-setup/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-weekly/SKILL.md
---

# Agentdev IWE workflow skills

## Purpose

The IWE workflow belongs to the `agentdev` catalog, so consuming projects
receive the skills through the installed plugin instead of inheriting hidden
repository-local Claude skills from `.claude/`.

## Behaviour

**The seven workflow skills live in the plugin.** Setup, Explore, Plan,
Implement, Verify, Ship, and Weekly are shipped from
`.agents/plugins/agentdev/skills/iwe-*/` and invoked as `/agentdev:iwe-*`.

**Skill-to-skill references are plugin-portable.** The workflow instructions use
namespaced `/agentdev:iwe-*` invocations for sibling handoffs, so the catalog
does not rely on repository-relative `.claude/skills/` paths.

**The template copy surface stays explicit.** `.claude/` remains project-facing
configuration, while the workflow skills travel with the installed `agentdev`
catalog described by the devcontainer lifecycle.

## References

- Plan:
  [Move the IWE workflow skills into the agentdev plugin](../plans/20260816-move-iwe-skills-to-agentdev.md)
- Specs: [Template consumption](../spec/template-consumption.md) and
  [IWE workflow skills](../spec/iwe-workflow-skills.md)
