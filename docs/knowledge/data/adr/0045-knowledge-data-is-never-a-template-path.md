---
type: adr
stage: accepted
---

# Knowledge data is never a template path

`docs/knowledge/data/` holds the project memory of this repository here and the
project memory of a consumer in that consumer: one path with two owners. The
template does not track this path, and `template-consume` never diffs it. A
consumer receives its workspace one time from the `iwe-bootstrap` scaffold in
the installed catalog.

## Considered Options

- Track `docs/knowledge/data/`. Rejected: each difference is the history of one
  owner, and applying it in either direction destroys the memory of the other
  owner.
- Seed the consumer from the template checkout. Rejected: it needs the checkout,
  and it starts the consumer from the memory of this repository.

## Consequences

- `docs/knowledge/LICENSE.md` is also not a template path, because bootstrap
  installs it and the consumer owns it after that.
- The scaffold is catalog content, and `iwe-bootstrap` uses it only one time. It
  is never in `tracked_paths`, so a catalog change to the scaffold never goes to
  a consumer that has a workspace.
