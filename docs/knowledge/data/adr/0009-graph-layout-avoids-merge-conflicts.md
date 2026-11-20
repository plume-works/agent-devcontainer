---
type: adr
stage: accepted
description: A state change edits only the file of the work item, the build order is a rank query, and each hub is one flat list sorted by key.
---

# The graph layout keeps parallel pull requests free of merge conflicts

Parallel pull requests each write project state into the graph. A spot that
every pull request edits turns parallel work into merge conflicts, and each
conflict costs a catch-up merge, a full CI run, and often a fresh AI review. So
a state change edits only the work item's own file, the build order is a `rank`
query rather than a file, and each hub is one flat list sorted by key.

## Considered Options

- `merge=union` or a custom merge driver on hubs. Rejected: GitHub decides
  mergeability without `.gitattributes` merge drivers, so a driver saves only a
  local resolution; the pull request still reports the conflict. On hubs a union
  merge is also wrong: it keeps a moved link in both places, brings back a
  deleted link, and can duplicate a heading that both sides add. A custom driver
  must also be registered in the Git configuration of every clone.
- A merge queue. Rejected: `main` does not require branches to be up to date, so
  no catch-up merge here is caused by staleness. A queue cannot enqueue a
  conflicting pull request, and it adds a CI run per queued pull request.
- Hubs with one section for each stage, sorted by key. Rejected: the sort
  removes most conflicts in long sections, but short sections and backlog
  priority buckets keep conflicting, and every ship still moves a link between
  sections.
- A roadmap file or `after:` dependencies as the order. Rejected: work ships
  from the head of the sequence, so parallel ships always edit adjacent lines. A
  dependency set is a partial order and leaves independent work unordered. Plan
  prose keeps the dependencies.
- Hubs generated from frontmatter, not committed. Rejected: it removes hub
  conflicts entirely, but it drops the browsable list and the tree of the IWE
  editor views, and it adds a generator to maintain.

## Consequences

- Git merges two insertions cleanly only when at least one unchanged line
  separates them, so any list where every writer inserts at the top or the end
  conflicts on every parallel write. Conflict reduction has to come from the
  layout, not from merge tooling.
- Ranks step by 100, and an inserted item takes the midpoint of its neighbours,
  so an insertion edits no other item. Only a reorder pull request renumbers.
- Two pull requests conflict in a hub only when their new members are adjacent
  in the sort order.
- A query selects documents by `type` and frontmatter, not by hub membership.
