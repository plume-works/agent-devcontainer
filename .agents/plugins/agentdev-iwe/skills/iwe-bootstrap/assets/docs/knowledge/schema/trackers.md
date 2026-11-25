# Trackers

A tracker is a living document that sessions edit in place. There are two, each
with `type: tracker` and `stage: living`.

- `data/product.md` — what the product is, its users, platforms, and stack. Its
  `## Constraints` section and its optional `## Authoring rules` section (the
  project's own rules for each document type) bind each plan and each document,
  so project-specific discipline lives in data, not in forked skill prompts.
  Plan and Ship read them before they write. Each session reads
  `data/product.md` first.
- `data/glossary.md` — the shared language of the project. See
  `schema/glossary.md`.
