---
type: adr
stage: accepted
description: A state change edits only the file of the work item, the build order is a rank query, and each hub is one flat list sorted by key.
---

# The graph layout keeps parallel pull requests free of merge conflicts

Each pull request writes project state. A place that each pull request edits
causes conflicts, and each conflict needs a merge, a CI run, and often a new AI
review. For this reason, a state change edits only the file of the work item.
The build order is a `rank` query and not a file. Each hub is one flat list
sorted by key.

## Considered Options

- `merge=union` or a custom merge driver on hubs. Rejected: GitHub ignores
  `.gitattributes` merge drivers when it decides if a pull request can merge. A
  union merge also keeps a moved link in two places and restores a deleted link.
  Also, each clone must register a custom driver in its Git configuration.
- A merge queue. Rejected: `main` does not require a branch to be up to date, so
  no merge is necessary because a branch is old. A queue cannot accept a pull
  request that has a conflict, and it adds a CI run for each pull request.
- Hubs with one section for each stage, sorted by key. Rejected: the sort
  removes most conflicts in long sections, but short sections still cause
  conflicts, and each ship moves a link between sections.
- A roadmap file or `after:` dependencies as the order. Rejected: work ships
  from the start of a sequence, so parallel ships edit adjacent lines. A set of
  dependencies leaves independent work in no order. Plan prose keeps the
  dependencies.
- Hubs that a script makes from frontmatter. Rejected: the graph loses the list
  to browse and the tree of the IWE editor view, and the script needs
  maintenance.

## Consequences

- Git merges two insertions without a conflict only when one or more unchanged
  lines are between them. A list where each writer adds at the start or at the
  end causes a conflict at each parallel write, so the layout, not merge tools,
  must prevent conflicts.
- The interval between two ranks is 100, and an insertion takes the midpoint of
  the two adjacent ranks, so an insertion edits no other item. Only a pull
  request that changes the order gives new numbers.
- Ship removes `rank`, so only work that did not ship has a `rank`. Equal ranks
  are valid, the key sorts them, and CI writes a warning for them.
- Ship writes no release page. Only the release cut writes one, so no file
  changes at each ship.
- Two pull requests conflict in a hub only when their new members are adjacent
  in the sort order.
- A query selects documents by `type` and frontmatter, not by hub membership.
