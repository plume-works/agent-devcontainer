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
- A merge queue. Rejected: `main` does not require a branch to be up to date, so
  no merge is necessary because a branch is old. A queue cannot accept a pull
  request that has a conflict, and it adds a CI run for each pull request.
- Hubs with one section for each stage. Rejected: short sections still cause
  conflicts, and each ship moves a link between sections.
- A roadmap file or `after:` dependencies as the order. Rejected: work ships
  from the start of a sequence, so parallel ships edit adjacent lines. A set of
  dependencies leaves independent work in no order.
- Hubs that a script makes from frontmatter. Rejected: the graph loses the list
  to browse and the tree of the IWE editor view, and the script needs
  maintenance.

## Consequences

- Two pull requests conflict in a hub only when their new members are adjacent
  in the sort order.
- A query selects documents by `type` and frontmatter, not by hub membership.
