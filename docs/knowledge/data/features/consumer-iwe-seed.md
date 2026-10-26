---
type: feature
stage: implemented
description: Any repository can receive a blank IWE workspace from the installed agentdev catalog, directly or through template adoption, without overwriting existing knowledge.
generated:
  by: claude-code/opus-5
  at: 2026-10-25T06:31:58Z
sources:
- resource: docs/knowledge/data/plans/20260905-consumer-iwe-seed.md
- resource: docs/knowledge/data/plans/20261023-reusable-iwe-bootstrap.md
- resource: .agents/plugins/agentdev/skills/iwe-bootstrap/SKILL.md
- resource: docs/knowledge/data/spec/template-consumption.md
- resource: docs/knowledge/data/architecture/template-boundary.md
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
---

# Reusable IWE bootstrap

## Purpose

A repository that adopts IWE needs a blank, valid knowledge workspace rather
than a copy of this publisher repository's project memory. The installed
agentdev catalog supplies that workspace itself, so an agent can initialize any
mounted repository without an agent-devcontainer source checkout, and full
template adoption uses the same initializer.

## Behaviour

**The installed catalog owns the scaffold.** `/agentdev:iwe-bootstrap` carries
the complete schema-compatible `.iwe/` and `docs/knowledge/` workspace —
schemas, configuration, knowledge instructions, MIT notice, and a starting graph
with product placeholders, onboarding tasks, hubs, and examples. The scaffold is
outside every live IWE graph and is the only source an initialization copies
from.

**Bootstrap is independently invokable and never overwrites.** It installs the
workspace only when `.iwe/` and `docs/knowledge/` are both absent, validates it,
and stops. A complete valid workspace is reported as already initialized with no
change; any partial, incompatible, or colliding state is reported for
reconciliation with nothing written. An interrupted run leaves only state the
next run recognizes and discards or completes.

**Onboarding stays separate.** Bootstrap names `iwe-setup` and then `iwe-map` as
the next operations and runs neither; it adds no CI or pre-commit configuration.

**Full adoption composes bootstrap.** Both template-consumption workflows invoke
bootstrap, then iwe-setup followed by iwe-map from the consumer root. Workflow A
first removes the copied publisher workspace only when it is proven
byte-identical to the adopted ref. The onboarding skills retain their interview
and confirmation gates, and mapping is deferred explicitly when no code exists.

**Consumer knowledge remains consumer-owned.** Existing or partially onboarded
knowledge is preserved and collisions are resolved with the user. Update mode
tracks only reusable support files, never publisher memory or the bootstrap
scaffold, never invokes bootstrap, and narrows legacy broad tracking before it
computes changes.

## Edge cases

- **No agent-devcontainer checkout is available.** Every scaffold file ships in
  the installed skill, so initialization makes no request to another repository.
- **Bootstrap runs again.** A complete valid workspace, onboarded or not, is
  reported as already initialized and left byte-for-byte unchanged.
- **A greenfield consumer.** Setup establishes product memory and the report
  defers mapping explicitly, since there is no code to map.
- **Onboarding input is still pending.** Adoption reports the pending work,
  keeps the current data, and does not declare onboarding complete or reset it
  on resumption.
- **Knowledge already exists.** A modified publisher copy, a partial workspace,
  or partial onboarding is preserved and collisions are resolved with the user,
  without bootstrapping.
- **The scaffold changes in a catalog update.** An update never applies scaffold
  or publisher memory changes to consumer memory and never reruns onboarding.
- **IWE is declined.** Bootstrap and onboarding are skipped and copied IWE-only
  artifacts are removed.

## Open questions

None — every design question this feature raised is settled.

## References

- Plans: [Repository-owned IWE seed for
  consumers](../plans/20260905-consumer-iwe-seed.md), [Extract a reusable IWE
  bootstrap skill](../plans/20261023-reusable-iwe-bootstrap.md)
- Spec: [Template consumption](../spec/template-consumption.md)
- Architecture: [Template boundary](../architecture/template-boundary.md)
