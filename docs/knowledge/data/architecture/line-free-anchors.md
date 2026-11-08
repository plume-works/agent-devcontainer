---
type: architecture
description: References name a place by symbol, heading slug, key path, or verbatim quote, never by line number; a pre-commit gate rejects line numbers and resolves the anchors in live documents.
sources:
- resource: scripts/check-anchors.py
- resource: AGENTS.md
- resource: docs/knowledge/data/plans/20261108-line-free-anchors.md
---

# Line-free anchors

## Decision

The maintainer's rule: never record a line number. A line number is wrong the
next time its file changes, so a plan's `## Key references`, a task's evidence,
a bug's references, and every skill's chat report name a place by an anchor
instead. The anchor syntax is specified in `spec/line-free-anchors` and stated
for agents in the repository `AGENTS.md`: `<path>::<symbol>` in code,
`<path>#<heading-slug>` in Markdown, `<path>#<key.path>` in YAML, JSON, and
TOML, `<path>#<target>` in a Makefile or Dockerfile, and any of those followed
by ` › "<verbatim quote>"` for a spot inside one, all in one code span.

An anchor stays true until its target is renamed or removed, and then it stops
resolving instead of silently pointing elsewhere, so it carries no date stamp.

## Enforcement

`scripts/check-anchors.py` runs as an always-run pre-commit hook, so the CI
pre-commit job runs it too. It runs on every commit rather than on a path filter
because a code rename anywhere can break a live anchor.

- **Line-number gate.** Scans `docs/knowledge/data/` and the agentdev catalog's
  skills and agents, fenced blocks included, for `<file.ext>:<N>`, an
  extensionless `Dockerfile`, `Makefile`, or `Containerfile` reference with a
  line, a `#L<N>` fragment, and prose `line <N>`.
- **Anchor resolver.** Resolves the anchors under `## Key references` in active
  plans and every anchor in open bugs and backlog items and in architecture
  documents. Anchors elsewhere in a plan are not resolved, because a plan's
  tasks name code it has not created yet; closed documents are not resolved,
  because the code they cite may since have been deleted.

Limits the maintainer accepted:

- The gate does not recognize a bare `:<N>` that continues an earlier reference.
  Agents follow the rule there; the gate does not hold it.
- A non-Python symbol resolves when each dotted segment occurs as a whole word
  in order, so a symbol moved into a comment still resolves.
- Chat reports, code comments, and PR bodies are outside the gate's reach and
  rest on the catalog's instructions.
- A link into another repository's file at a pinned commit keeps its line
  fragment: the target cannot change, and an anchor names only this repository's
  code. The research case studies under `docs/research/` cite sources this way
  and are outside the gate.
- A placeholder written as a real path in an architecture document or open bug
  is resolved like any anchor; write placeholders in angle brackets.

## Rejected alternatives

- **Line numbers with a date stamp.** The stamp tells a reader how far to trust
  the number but does not keep it true; about half of a plan's stamped anchors
  pointed at the wrong line by the time it shipped.
- **Planting anchors in target files** (`<a id>`, `anchor:` comments). Every
  reference would edit the file it points at, and a symbol or heading already
  identifies the spot.
- **Exempting closed documents from the gate.** Agents copy the shape they read,
  and the exemption would need its own rule; every existing reference was
  rewritten instead.
