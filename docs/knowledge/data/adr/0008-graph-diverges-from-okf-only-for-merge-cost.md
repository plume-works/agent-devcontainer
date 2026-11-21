---
type: adr
stage: accepted
---

# The graph is different from OKF only where OKF causes merge work

The graph stays an OKF v0.2 bundle and diverges from OKF only to cut merge or
upkeep cost. `generated.at` changed on every edit, so two branches that touched
one document collided in its frontmatter even when their content did not. That
merge cost, with review noise and upkeep, is why no document under `data/` sets
`generated` or `verified`; Git already records when and by whom a document
changed. No document sets `status`, because it duplicates `stage`, the lifecycle
field.

## Considered Options

- Set `status` next to `stage`. Rejected: every state change then edits two
  fields, and OKF makes `status` optional.
- Remove the declaration of the keys from `okf.yaml`, and add no check.
  Rejected: `okf.yaml` accepts undeclared fields, so dropping a declaration does
  not keep the key out of a document. The ban has to be a check, and one check
  covers `status`, `generated`, and `verified`.

## Consequences

- `sources` stays. It records what a document derives from, and it does not
  change on every edit.
- `data/index.md` stays as OKF requires. It lists only hubs and changes only
  when a hub is added, so it costs no merges.
