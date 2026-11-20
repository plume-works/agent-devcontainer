---
type: adr
stage: accepted
description: Committed text names a place in a file by an anchor and never by a line number, and `scripts/check-anchors.py` holds the rule on each commit.
---

# Committed text names places by anchors, not by line numbers

The maintainer does not permit a line number in committed text. An anchor stays
correct until its target is renamed or removed, and then it stops resolving
rather than silently pointing elsewhere, so it carries no date stamp.
`scripts/check-anchors.py` runs on each commit with no path filter, because a
code rename anywhere can break a live anchor. A live anchor is an anchor that
the check resolves: in the `## Key references` of an active plan, in an open bug
or task, or in a guide.

## Considered Options

- Line numbers with a date. Rejected: the date tells the reader how much to
  trust the number, but it does not keep the number correct.
- Anchors planted in the target files, such as `<a id>` or `anchor:` comments.
  Rejected: each reference would edit the file that it points at, while a symbol
  or a heading already identifies the place.
- Exempting closed documents from the line-number check. Rejected: agents copy
  the shape of what they read, and the exemption would need its own rule.

## Consequences

- The check resolves only live anchors. The tasks of a plan name code that does
  not exist yet, and a closed document can name code that a later change
  removed.
- Only the catalog instructions control the anchors in chat reports, code
  comments, and pull request bodies.
