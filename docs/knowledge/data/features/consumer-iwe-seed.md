---
type: feature
stage: implemented
description: Consumers can adopt a repository-owned IWE seed and initialize project memory without overwriting consumer-authored knowledge.
generated:
  by: claude-code/opus-5
  at: 2026-09-06T05:39:02Z
sources:
- resource: docs/knowledge/data/plans/20260905-consumer-iwe-seed.md
- resource: docs/knowledge/data/spec/template-consumption.md
- resource: docs/knowledge/data/architecture/template-boundary.md
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
---

# Consumer IWE seed

## Purpose

An IWE consumer needs a blank, valid knowledge workspace rather than a copy of
this publisher repository's project memory. The reusable seed supplies that
starting state from the adopted agent-devcontainer ref without retaining a
dependency on its original import source.

## Behaviour

**The repository owns the seed.** `templates/iwe/data/` contains the complete
schema-compatible starting graph, including product placeholders, onboarding
tasks, hubs, and examples. The seed remains outside the publisher's active IWE
graph and carries its MIT notice into each consumer.

**Fresh adoption initializes consumer memory.** Both template-consumption
workflows install the reusable scaffold and seed, then invoke iwe-setup followed
by iwe-map from the consumer root. The onboarding skills retain their interview
and confirmation gates, and mapping is deferred explicitly when no code exists.

**Consumer knowledge remains consumer-owned.** Existing or partially onboarded
knowledge is preserved and collisions are resolved with the user. Update mode
tracks only reusable support files, never publisher memory or initialization
seed content, and narrows legacy broad tracking before it computes changes.

## References

- Plan:
  [Repository-owned IWE seed for consumers](../plans/20260905-consumer-iwe-seed.md)
- Spec: [Template consumption](../spec/template-consumption.md)
- Architecture: [Template boundary](../architecture/template-boundary.md)
