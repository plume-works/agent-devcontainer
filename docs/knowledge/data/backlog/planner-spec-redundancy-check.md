---
type: task
stage: done
priority: high
created: 2026-11-09
description: Make the planner check a spec delta against the rest of its spec, so a change neither restates an existing rule nor carries forward a scenario it made redundant.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: openspec/specs/iwe-workflow-skills/spec.md
completed: 2026-11-09
---

# Stop the planner from adding spec redundancy

A durable spec shrinks only when a plan's `## Spec changes` says so: Ship merges
the delta and preserves every requirement and scenario the delta does not touch
(`docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-ship-synchronizes-durable-specs-by-intelligent-merge`).
The planner is what decides the delta, and nothing in it looks past the
requirement being edited:

- `iwe-planner.agent.md` requires a `MODIFIED` requirement to carry "*every*
  surviving scenario", so an edit carries old scenarios forward by default and
  dropping one is never prompted.
- No rule checks whether an `ADDED` requirement restates a rule another
  requirement of the same spec already holds.

The result is a spec that only grows: each plan adds its rule to the phase it
touches, beside the copies other phases already hold. Without this fix, [Remove
redundancy from the durable specs](deduplicate-spec-requirements.md) is undone
by the next plans that touch the same specs.

## What to do

Add a planner rule, applied whenever a plan writes a structured delta: before
validation, read the whole target spec and

- reference a rule's existing home requirement instead of restating it;
- in a `MODIFIED` block, drop each scenario the change leaves restating its
  requirement, and say so as a deliberate removal.
