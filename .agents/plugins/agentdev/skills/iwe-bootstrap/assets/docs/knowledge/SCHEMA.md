# Frontmatter reference

The human-readable companion to the machine schemas. Validation lives in
`.iwe/schemas/*.yaml`, bound to key globs in `.iwe/config.toml` (`[schemas]`
section) — bindings are by path, and **every** document under `data/` is bound,
hubs included. Run `iwe schema validate` before committing — exit 0 is the gate.

The examples below describe one fictional product (Pomodux, a focus-timer app);
the `*.example.md` docs demonstrate each shape in place.

Every document under `data/` carries a non-empty `type` —
`.iwe/schemas/base.yaml` enforces it, because every query selects documents by
it. `data/log.md` is the one exception and has a shape of its own. The per-type
blocks below show only the fields specific to that type; the shared families
come next.

## Fields every type carries

Declared on every schema:

- `description` — one sentence. Every document has one; it is what a reader sees
  in query results before opening the file.
- `generated` — `{ by, at }`. Write it on **every** edit. `by` is an actor:
  `<producer>/<model-version>` for agent writes — the agent and the model
  version that wrote the content; `human:<handle>` for hand-authored or
  human-confirmed content; `process:<id>` for automation.
- `sources` — the materials a document derives from, each
  `{ id, resource, title, author, usage_count, last_modified }` with `resource`
  required. A `resource` may be a URL or a repo path. Attribute individual
  claims with a markdown footnote keyed to an entry's `id`.
- `verified` — `{ by, at }` or a list, recording who confirmed the content
  against its sources.
- `resource`, `tags`, `stale_after`, `usage_window` — optional.

`stage` is the only lifecycle field: the per-type enums below. A work item's
state lives only in its own frontmatter; no hub section repeats it.

## The build order — `rank`

Active plans, open bugs, and planned backlog tasks may carry `rank`, a positive
integer: their place in one build order shared across the three types, lower
first.

``` yaml
rank: 300 # optional; positive integer
```

- The sequence is
  `iwe find --filter '{rank: {$exists: true}}' --sort rank:1 -f keys`. An item
  without `rank` is not yet sequenced; that is the separate
  `rank: {$exists: false}` query, never part of the sequence.
- Ranks step by 100; an insertion takes the midpoint of its neighbours. Only a
  reorder pull request renumbers.
- Ship removes `rank` from a plan, bug, or task it marks done or cancelled.
- Equal ranks are valid and break by key; CI warns about them.

## The log — `data/log.md`

The update history, written only by a release cut. It has no frontmatter, and
`.iwe/schemas/log.yaml` checks its body: a title section over `## YYYY-MM-DD`
groups of bullets, newest first.

## Plans — `data/plans/YYYYMMDD-<slug>.md`

Implementation plans, migrations, and design proposals.

``` yaml
---
type: plan # required
stage: done # done | cancelled — omit while active/pending
created: 2026-07-01 # required, YYYY-MM-DD
completed: 2026-07-18 # required when stage: done
release: # required while active: internal, or the keys below
- features/focus-sessions
---
```

`release` is the plan's release impact, chosen when the plan is written:
`internal` when no workspace user or template consumer sees a difference,
otherwise the `features/` and `bugs/` keys the work adds, changes, or fixes. The
release cut takes the plan's release entries from it.

Body: `## Context`, `## Approach`, `## Implementation Steps` (`### Task N`,
`**Files:**`, checkboxes), `## Spec changes`, `## Depends on` (optional),
`## Verification`, `## Out of scope`, `## Key references` (dated
`path:line — symbol` anchors). Its link in `data/plans.md` never moves.

## Features — `data/features/<slug>.md`

Feature design documents; the stage carries the whole lifecycle.

``` yaml
---
type: feature # required
stage: implemented # proposed | accepted | implemented | deprecated | cancelled — required
---
```

Body: `## Purpose`, `## Behaviour`, `## Edge cases`, `## Open questions`.

## Bugs — `data/bugs/<slug>.md`

Bug reports and investigations. H1 starts with `Bug:`.

``` yaml
---
type: bug # required
stage: done # done | cancelled — omit while open
---
```

Body: `## Symptom`, `## Reproduction`, `## Root cause`, `## Fix`,
`## Key references`.

## Releases — `data/releases/<version>.md`

One page per cut version, written only by the release cut from the plans
completed since the previous release and their `release` lists.

``` yaml
---
type: release # required
version: 0.1.0 # required
date: 2026-07-18 # the day the release was cut
stage: released # required, always released
---
```

Body: `## Added` / `## Changed` / `## Fixed` as inclusion links to feature and
bug docs. A feature already released in an earlier version, but which gained
behavior in this one, belongs under `## Changed` rather than `## Added`.

## Backlog tasks — `data/backlog/<slug>.md`

Atomic prioritized work items waiting to become plans.

``` yaml
---
type: task # required
stage: planned # planned | done | cancelled — required
priority: high # high | medium | low
created: 2026-08-01 # required, YYYY-MM-DD
completed: 2026-08-14 # set when done
---
```

## Reference documents — type only

`data/spec/`, `data/architecture/`, `data/concept/`, and `data/someday/` docs
carry a `type` (`spec`, `architecture`, `concept`, `someday`) and nothing else
that is required: they are durable reference, not work items, so no `stage`
applies. Specs use the Requirement/Scenario format (`### Requirement:` + SHALL,
`#### Scenario:` + WHEN/THEN); architecture notes record decisions with their
rejected alternatives.

## Hubs and the trackers

Hub files (`data/plans.md`, `data/features.md`, …) carry `type: hub`;
`data/product.md` and `data/milestone.md` carry `type: tracker`. Both take
`stage: living`. A hub's body is one flat list of inclusion links, one per
member, sorted by the member's key with any `YYYYMMDD-` prefix removed, with no
`##` sections — `.iwe/schemas/hub.yaml` rejects a section, and a test checks the
order. A hub changes only when a member is created, removed, or renamed.
