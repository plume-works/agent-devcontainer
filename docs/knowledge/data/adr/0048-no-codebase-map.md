---
type: adr
stage: accepted
description: The graph keeps no codebase map and the catalog ships no map skill; update mode removes a map that is no longer used from a consumer without a question.
---

# The graph keeps no codebase map

The graph keeps no `data/codebase/` map, and the catalog ships no map skill. No
workflow skill or agent read the map. A source digest proved only that a map
document had a new stamp, not that its text was correct. Each pull request that
changed mapped code paid for a refresh, a CI gate, and digest lines that
conflict between branches. A new reader uses the code and the README to find a
path.

## Considered Options

- One orientation page in its place. Rejected: it duplicates the README.
- A digest gate that only warns. Rejected: it keeps the refresh cost and the
  risk of wrong text.
- Tell planners to read text that a tool derived from the code. Rejected: no
  check confirms that text.

## Consequences

- Update mode of `template-consume` removes the codebase map of a consumer
  without a question. The installed catalog no longer ships `stale-map-docs.py`,
  so a kept map leaves a CI step or hook that cannot pass.
