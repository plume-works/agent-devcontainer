---
type: architecture
description: Why work-item state lives only in frontmatter, the build order is a global rank field, hubs are flat alphabetical membership lists, the log and release pages are written only at a release cut, and the graph does not follow OKF.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T12:00:00Z
sources:
- resource: .iwe/config.toml
- resource: .iwe/schemas/hub.yaml
- resource: docs/knowledge/AGENTS.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-capture/SKILL.md
---

# Conflict-free knowledge layout

Parallel pull requests each write project state into the graph. A file every
pull request edits at the same spot turns parallel work into merge conflicts,
and each conflict costs a catch-up merge, a full CI run, and often a fresh AI
review. The layout below gives every write a single owner: a document's own
file, or the release cut.

## Decisions

- **Frontmatter is the only record of a work item's state.** `stage`,
  `priority`, `completed`, and `rank` live in the item's own document. No hub
  section repeats them, so a stage change edits one file that only its own pull
  request touches.
- **One global build order, `rank:`.** Active plans, open bugs, and planned
  backlog tasks share an integer `rank`; lower builds first. Ranks step by 100
  and an inserted item takes the midpoint of its neighbours. An item without a
  `rank` is not yet sequenced. Ship removes `rank`, so only unshipped work
  carries one. Equal ranks are allowed and break by key; CI warns about them.
  Renumbering happens only in a reorder pull request.
- **The order is a query, not a file.**
  `iwe find --filter '{rank: {$exists: true}}' --sort rank:1` lists the sequence
  across all three types. The `$exists: true` filter is part of the order query;
  unsequenced work is a second query (`rank: {$exists: false}`), never part of
  the first.
- **Hubs are flat alphabetical membership lists.** A hub holds one inclusion
  link per member, ordered by the member's key without a `YYYYMMDD-` prefix, and
  no `##` sections. A hub is edited only when a member is created, removed, or
  renamed. Two pull requests then conflict only when their new members sort next
  to each other.
- **Membership is the frontmatter `type`.** Queries select documents by `type`
  and frontmatter fields, not by `--included-by <hub>`; hubs remain as browsable
  lists and as the graph's tree for the IWE editor views.
- **The log and release pages are written only at a release cut.** Ship writes
  neither. The cut builds `releases/<X.Y.Z>.md` from the plans completed since
  the previous release and their `release` lists, and adds one dated group to
  `log.md`. There is no `releases/unreleased.md` accumulator.
- **The graph does not follow OKF.** There is no `data/index.md`, no `okf-index`
  or `okf-log` body schema, and no `status` field. A base schema still requires
  a non-empty `type` on every document under `data/`, because every query
  depends on it.

## Constraints

- GitHub decides mergeability without `.gitattributes` merge drivers. A
  `merge=union` or custom driver resolves a conflict only in a local merge; the
  pull request still reports a conflict, and the catch-up merge and its CI run
  still happen. Conflict reduction therefore has to come from the layout, not
  from merge tooling.
- Git merges two insertions cleanly only when at least one unchanged line
  separates them. Any list where every writer inserts at the top or the end
  conflicts on every parallel write.

## Rejected alternatives

- **`merge=union` on the log and hubs.** GitHub ignores it, so it saves only the
  agent's local resolution. On hubs it is also wrong: a link one side moves
  between sections survives in both places, a link one side deletes comes back
  as a dangling link, and a date heading both sides add can appear twice.
- **A custom merge driver.** Same GitHub limitation, and every clone would need
  the driver registered in its git configuration.
- **A merge queue.** `main` does not require branches to be up to date, so no
  catch-up merge in this repository is caused by staleness. A merge queue cannot
  enqueue a conflicting pull request and adds a CI run per queued pull request.
- **Keeping stage sections, sorted alphabetically.** Sorting removes most
  conflicts in long sections such as `## Done`, but short sections such as
  `## Active` and backlog priority buckets keep conflicting, and every ship
  still moves a link between sections.
- **A separate roadmap file listing the sequence.** Work ships from the head of
  the sequence, so parallel ships always edit adjacent lines.
- **Dependencies (`after: [keys]`) as the order.** A dependency set is a partial
  order and leaves independent work unordered. Plan prose keeps them.
- **Hubs generated from frontmatter, not committed.** Removes hub conflicts
  entirely but drops the browsable list and the editor tree, and adds a
  generator to maintain.
