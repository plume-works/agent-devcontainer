---
type: adr
stage: accepted
description: Each decision is one short ADR in data/adr/, proposed by Plan, accepted by Ship, and never edited after that.
---

# Each decision is a short ADR in the graph

A decision and its rejected options were entries in the `## Rationale` of a
spec, edited in place, and the code contradicts 4 of the 189 entries. Each
decision is one short document at `data/adr/NNNN-<slug>.md` that Plan proposes
and Ship accepts. An accepted ADR is never edited: a new ADR supersedes it, so
that a reader sees each decision as it was made.

## Considered Options

- A folder outside the graph. Rejected: `iwe` checks no link and no stage there.
- The MADR template. Rejected: its sections fill with text that says nothing.
