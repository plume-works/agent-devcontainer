---
type: adr
stage: accepted
description: A bug keeps its own optional Fix section, and a backlog task has no planned stage.
---

# A bug records its own correction

A bug reaches `done` by two routes, and many bugs are fixed directly by a pull
request that no plan references. Only the bug's own section can record those
fixes, so `.iwe/schemas/bug.yaml` permits `## Fix`, and Ship writes it when it
closes a bug. Backlog tasks do not get the bug lifecycle: a task's job ends when
a plan grows from it, so `.iwe/schemas/task.yaml` has no `planned` stage, and
`planned` means only that a plan owns a bug.

## Considered Options

- Drop `## Fix` and send the reader to the fixing plan through
  `iwe find --references`. Rejected: a bug fixed without a plan is then left
  with no record of its fix.

## Consequences

- A bug does not need `## Key references`. Its anchors rot with the code, while
  its `sources` frontmatter already names the paths that the bug derives from.
