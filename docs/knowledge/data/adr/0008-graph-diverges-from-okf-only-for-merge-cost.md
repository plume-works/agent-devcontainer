---
type: adr
stage: accepted
description: The graph follows OKF v0.2 and is different only where OKF causes merge or maintenance work, so no document sets status, generated, or verified.
---

# The graph is different from OKF only where OKF causes merge work

The graph follows OKF v0.2. It is different only where OKF causes merge work or
maintenance work. `generated.at` changed at each edit, so two branches that
edited one document had a conflict in its frontmatter. For this reason, no
document under `data/` sets `generated` or `verified`, because Git records when
and by whom a document changed. No document sets `status`, because `stage` is
the lifecycle field.

## Considered Options

- Set `status` next to `stage`. Rejected: each state change then edits two
  fields, and OKF makes `status` optional.
- Remove the declaration of the keys from `okf.yaml`, and add no check.
  Rejected: `okf.yaml` accepts fields that it does not declare, so only a check
  can stop a key.

## Consequences

- The `banned-frontmatter-keys` pre-commit check
  (`docs/knowledge/tests/test_banned_frontmatter_keys.py::BANNED_KEYS`) rejects
  a document that sets one of the three keys.
- `sources` stays. It records what a document comes from, and it does not change
  at each edit.
- `data/index.md` stays as OKF requires. It lists only hubs and changes only
  when the graph gets a new hub, so it causes no merge work.
