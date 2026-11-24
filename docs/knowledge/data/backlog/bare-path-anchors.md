---
type: task
stage: pending
priority: medium
created: 2026-11-08
description: Decide if scripts/check-anchors.py must also check that a bare back-ticked path names a file that exists, or if a bare path stays a reference that the resolver does not check.
sources:
- resource: scripts/check-anchors.py
- resource: docs/knowledge/data/plans/20261108-line-free-anchors.md
---

# Resolve bare-path anchors or narrow the anchor rule

`AGENTS.md#best-practices-for-agents` › "NEVER RECORD LINE NUMBERS" counts a
bare `<path>` that names a full file as an anchor, and says that
`scripts/check-anchors.py` enforces the graph and the catalog.
`scripts/check-anchors.py::anchors` gives only spans that hold `::`, `#`, or a
quote, as Task 2 of the line-free anchors plan defines an anchor. So a bare
back-ticked path under an active plan's `## Key references`, in an open bug or
backlog item, or in a guide is never checked for existence. The rule and the
code disagree until one of them changes.

The work is to decide one of:

- **Resolve bare paths.** The resolver checks that a bare-path span in its scope
  names an existing file. It has to tell a path from other back-ticked tokens
  that look like one, such as a file name without a directory.
- **Narrow the rule.** The resolver checks only `::`, `#`, and quoted anchors,
  and a bare path stays an unchecked reference to a whole file. Record this
  limit where the rule is.
