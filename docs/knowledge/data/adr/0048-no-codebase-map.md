---
type: adr
stage: accepted
description: The graph keeps no data/codebase/ documents and the catalog contains no map skill; update mode removes these documents from a consumer without a question.
---

# The graph keeps no map of the code

The graph keeps no `data/codebase/` map, and the catalog contains no map skill.
No workflow skill or agent read the map. A source digest proved only that a map
document had a new stamp, not that its text was correct. Each pull request that
changed mapped code paid for an update of the map, a CI check, and digest lines
that conflict between branches. A new reader uses the code and the README to
find a path.

## Considered Options

- One orientation page in its place. Rejected: it duplicates the README.

## Consequences

- Update mode of `template-consume` removes the `data/codebase/` documents of a
  consumer without a question. The installed catalog no longer contains
  `stale-map-docs.py`, so a kept map leaves a CI step or hook that cannot pass.
