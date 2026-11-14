---
type: adr
stage: accepted
description: The template never tracks docs/knowledge/data/, and a consumer receives its knowledge workspace from the iwe-bootstrap scaffold in the installed catalog.
---

# Knowledge data is never a template path

`docs/knowledge/data/` holds the project memory of the publisher here and the
project memory of the consumer in a consumer: one path with two owners. The
template does not track this path, and `template-consume` never diffs it. A
consumer receives its workspace one time from the `iwe-bootstrap` scaffold in
the installed catalog.

## Considered Options

- Track `docs/knowledge/data/`. Rejected: each difference is the history of one
  owner, and to apply it in either direction destroys the memory of the other.
- Copy the memory into the consumer from the template checkout. Rejected: it
  needs the checkout, and the consumer starts with the memory of the publisher.

## Consequences

- `docs/knowledge/LICENSE.md` is also not a template path, because bootstrap
  installs it and the consumer owns it after that.
- The scaffold is catalog content, and `iwe-bootstrap` uses it only one time. It
  is never in `tracked_paths`, so a catalog change to the scaffold never gets to
  a consumer that has a workspace.
- `iwe-bootstrap` never deletes, overwrites, or merges an existing `.iwe/` or
  `docs/knowledge/`. The update mode of `template-consume` never runs
  `iwe-bootstrap` or `iwe-setup`.
- `.iwe/` and the support documents and tests in `docs/knowledge/` are template
  paths. A consumer that keeps the knowledge workspace tracks them.
