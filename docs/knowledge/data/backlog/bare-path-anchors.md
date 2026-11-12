---
type: task
stage: pending
priority: medium
created: 2026-11-08
description: Make the anchor resolver check bare-path anchors, or narrow the "Live anchors resolve" requirement to `::`, `#`, and quoted anchors, so the code and the spec agree.
sources:
- resource: scripts/check-anchors.py
- resource: docs/knowledge/data/plans/20261108-line-free-anchors.md
---

# Resolve bare-path anchors or narrow the live-anchor requirement

The [line-free anchors
plan](../archive/3.0.0/plans/20261108-line-free-anchors.md)'s spec delta for
`spec/line-free-anchors` counts a bare `<path>` naming a whole file as an anchor
(Requirement "References never record a line number"), and Requirement "Live
anchors resolve" says every anchor in the resolver's scope SHALL resolve.
`scripts/check-anchors.py::anchors` yields only spans holding `::`, `#`, or a
quote, as the plan's Task 2 defines an anchor, so a bare back-ticked path under
an active plan's `## Key references`, in an open bug or backlog item, or in an
architecture document is never checked for existence. Code and spec disagree
until one of them changes.

The work is to decide one of:

- **Resolve bare paths.** The resolver checks that a bare-path span in its scope
  names an existing file. It has to tell a path from other back-ticked tokens
  that look like one, such as a file name without a directory.
- **Narrow the requirement.** "Live anchors resolve" covers every `::`, `#`, or
  quoted anchor, and a bare path stays an unchecked reference to a whole file.
