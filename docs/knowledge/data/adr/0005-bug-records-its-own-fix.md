---
type: adr
stage: accepted
description: A bug keeps its own optional Fix section, and a backlog task has no planned stage.
---

# A bug records its own correction

A bug reaches `done` by two routes, and a pull request that no plan names
corrects many bugs directly. Only a section in the bug can record such a
correction, so `.iwe/schemas/bug.yaml` permits `## Fix`, and Ship writes it when
it closes a bug. A backlog task stops when a plan starts from it, so
`.iwe/schemas/task.yaml` has no `planned` stage.

## Considered Options

- No `## Fix`: the reader finds the plan that corrected the bug through
  `iwe find --references`. Rejected: a bug that a pull request corrected without
  a plan then has no record of its correction.

## Consequences

- A bug does not need `## Key references`. Its anchors become wrong when the
  code changes, and its `sources` frontmatter names its paths.
