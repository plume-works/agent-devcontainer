---
type: adr
stage: accepted
description: The graph keeps no data/codebase/ documents and the catalog contains no map skill; update mode removes these documents from a consumer without a question.
---

# The graph keeps no codebase map

The graph keeps no `data/codebase/` map, and the catalog contains no map skill.
No workflow skill or agent was told to read the map. A stamped source digest
proved only that a map document was re-stamped, not that its text was correct.
Every pull request that touched mapped code paid for a map refresh, a CI gate,
and digest lines that conflict between branches. A new reader uses the code and
the README to find a path.

## Considered Options

- One orientation page in its place. Rejected: it duplicates the README.

## Consequences

- Update mode of `template-consume` removes the `data/codebase/` documents of a
  consumer without a question, although migrating a consumer's documents is
  otherwise the user's decision. The installed catalog no longer ships
  `stale-map-docs.py`, so a kept map would leave a CI step or hook that cannot
  pass.
