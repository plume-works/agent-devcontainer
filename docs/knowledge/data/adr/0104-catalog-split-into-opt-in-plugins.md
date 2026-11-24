---
type: adr
stage: accepted
supersedes:
- adr/0011-iwe-skills-in-agentdev-with-iwe-prefix
---

# The catalog is split into opt-in plugins, and the IWE workflow is its own plugin

`agentdev` has grown into a monolith. Its skills differ in how much they impose.
The `pr-*` and git skills are generic enough for any repository. The IWE skills
are heavy and prescriptive: they assume a knowledge graph and a fixed plan →
implement → ship workflow. Most of them can be started by the model on their
own, so they intrude on sessions that never asked for them. Users should be able
to choose which skill sets they install. The IWE workflow moves to its own
plugin, `agentdev-iwe`. This is the first of several splits.

The maintainer made this decision. One marketplace publishes every plugin, and a
plugin can use the skills and agents of `agentdev`.

## Considered Options

- One plugin, as ADR-0011 decided. Rejected: a user cannot opt out of the IWE
  workflow.

## Consequences

- Each plugin is versioned on its own, and a user enables each one separately.
- A skill in `agentdev` that names an IWE skill names a skill that a user
  without `agentdev-iwe` does not have.
