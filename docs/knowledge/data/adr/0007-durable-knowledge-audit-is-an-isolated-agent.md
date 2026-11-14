---
type: adr
stage: accepted
description: The durable-knowledge audit runs in an agent that did not see the work and cannot edit the file, with its rule in the one rulebook iwe-audit.
---

# The durable-knowledge audit runs in an isolated agent

A writer reads a draft through the session that wrote it, so residue from that
session stays in the draft. For this reason, the audit runs in the Durable
Knowledge Auditor, which did not see the work and cannot edit what it reads. The
rule is in one rulebook, `iwe-audit`. Each change to the intent of a plan goes
through Plan, so one gate in `/agentdev:iwe-plan-review` covers each mode of
Plan.

## Considered Options

- An audit step in the context of Plan. Rejected: it reads the draft through the
  same context that wrote it.
- Each caller copies the rule into the prompt of a subagent. Rejected: each copy
  becomes different.
- A script in the plan shape gate that finds a story of the work. Rejected: a
  story has no shape. A length or prose ratio rule fails on long plans and
  misses a short story.
- `## Context` and `## Approach` are read-only to Implement. Rejected: correct
  changes to intent come during Implement, and the material deviation route
  handles them.
