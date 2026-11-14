---
type: adr
stage: accepted
description: Committed text names a place in a file by an anchor and never by a line number, and `scripts/check-anchors.py` holds the rule on each commit.
---

# Committed text names places by anchors, not by line numbers

The maintainer does not permit a line number in committed text. An anchor stays
correct until its target gets a new name or its file loses it. Then the check
cannot resolve it, and it does not point to a different place.
`scripts/check-anchors.py` runs on each commit with no path filter, because a
code rename anywhere can break a live anchor.

## Considered Options

- Line numbers with a date. Rejected: the date tells the reader how much to
  trust the number, but it does not keep the number correct.
- Anchors written into the target files, such as `<a id>` or `anchor:` comments.
  Rejected: each reference then changes the file that it points to, but a symbol
  or a heading already identifies the place.
- No line-number check for closed documents. Rejected: agents copy the form of
  what they read, and the exception needs its own rule.

## Consequences

- An anchor is one code span: `<path>::<symbol>` in code,
  `<path>#<heading-slug>` in Markdown, `<path>#<key.path>` in YAML, JSON, and
  TOML, and `<path>#<target>` in a Makefile or a Dockerfile. A spot inside one
  of these adds ` › "<verbatim quote>"`.
- The line-number check examines `docs/knowledge/data/` and the skills and
  agents of the agentdev catalog, and also their fenced blocks.
- The resolver examines only live anchors. The tasks of a plan name code that
  does not exist yet, and a closed document can name code that a later change
  removed.
- The resolver examines a real path in a live anchor as an anchor, so a
  placeholder path goes in angle brackets.
- The check does not find a bare `:N` after an earlier reference. A symbol that
  is not Python resolves when its parts occur as whole words in sequence.
- Chat reports, code comments, and pull request bodies rely only on the catalog
  instructions.
- The check also reports the `#L` line fragment of a link to a file of a
  different repository at a fixed commit.
