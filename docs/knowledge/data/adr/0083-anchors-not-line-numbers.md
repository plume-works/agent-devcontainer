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

- The check does not find a bare `:N` after an earlier reference. A symbol that
  is not Python resolves when its parts occur as whole words in sequence.
- Chat reports, code comments, and pull request bodies rely only on the catalog
  instructions.
- A link to a file of a different repository at a fixed commit can keep its line
  fragment, because that target cannot change.
