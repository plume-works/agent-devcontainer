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
- Seed the consumer from the template checkout. Rejected: it needs the checkout,
  and the consumer starts with the memory of the publisher.

## Consequences

- `docs/knowledge/LICENSE.md` is also not a template path, because bootstrap
  installs it and the consumer owns it after that.
