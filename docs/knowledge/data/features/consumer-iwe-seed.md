---
type: feature
stage: implemented
description: Consumers can adopt a repository-owned IWE seed and initialize project memory without overwriting consumer-authored knowledge.
generated:
  by: claude-code/opus-5.5
  at: 2026-09-27T09:48:53Z
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

## Edge cases

- **The initial import repository is gone.** Every seed file comes from
  agent-devcontainer at the adopted ref, so adoption makes no request to it.
- **A greenfield consumer.** Setup establishes product memory and the report
  defers mapping explicitly, since there is no code to map.
- **Onboarding input is still pending.** Adoption reports the pending work,
  keeps the current data, and does not declare onboarding complete or reset it
  on resumption.
- **Knowledge already exists.** A modified publisher copy or partial onboarding
  is preserved and collisions are resolved with the user, without reseeding.
- **The seed changes upstream.** An update never applies seed or publisher
  memory changes to consumer memory and never reruns onboarding.
- **IWE is declined.** Seeding and onboarding are skipped and copied IWE-only
  artifacts are removed.

## Open questions

None — every design question this feature raised is settled.

## References

- Plan:
  [Repository-owned IWE seed for consumers](../plans/20260905-consumer-iwe-seed.md)
- Spec: [Template consumption](../spec/template-consumption.md)
- Architecture: [Template boundary](../architecture/template-boundary.md)
