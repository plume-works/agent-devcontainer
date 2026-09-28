---
type: feature
stage: implemented
description: Template consumers can resume interrupted setup and preserve settled choices across later update episodes.
generated:
  by: claude-code/opus-5.5
  at: 2026-09-27T09:48:53Z
sources:
- resource: docs/knowledge/data/plans/20260906-template-consumption-progress.md
- resource: docs/knowledge/data/spec/template-consumption.md
- resource: docs/knowledge/data/architecture/template-boundary.md
- resource: docs/knowledge/data/architecture/agent-metadata-files.md
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
---

# Resumable template consumption

## Purpose

Template adoption and update episodes can span multiple sessions without losing
completed work or requiring consumer intent to be inferred again from a diff.

## Behaviour

**Progress is durable from the start.** Setup writes a consumer-owned
`.agentdev-template-progress.md` after workflow selection and before executing
the guide. Its task evidence and accumulated choice log let later sessions
resume unticked work and retain settled customization decisions.

**Machine state has one authority.** The root-only `template-consume` section of
`.agent.metadata.json` owns `consumed_ref` and tracked paths. Update mode
migrates the legacy marker without advancing the ref and couples the marker and
progress document when an episode completes.

**Consumers with IWE retain adoption context.** Setup and update refresh a thin
`data/template-adoption` summary containing the adopted SHA, workflow, choices,
and a pointer to the live progress record. Consumers without IWE skip it.

## Edge cases

- **Setup is interrupted.** The next session continues from the unticked tasks
  and recorded choices instead of restarting the interview.
- **A legacy `.agentdev-template.json`.** Update mode moves its fields into
  `.agent.metadata.json` and deletes it without advancing `consumed_ref`.
- **A changed path the choice log records as customized.** The recorded choice
  is applied and the path is merged by hand rather than overwritten.
- **A consumer without IWE.** No `data/template-adoption` summary is written.

## Open questions

None — every design question this feature raised is settled.

## References

- Plan:
  [Track template consumption progress and choices](../plans/20260906-template-consumption-progress.md)
- Spec: [Template consumption](../spec/template-consumption.md)
- Architecture: [Template boundary](../architecture/template-boundary.md) and
  [Agent metadata files](../architecture/agent-metadata-files.md)
