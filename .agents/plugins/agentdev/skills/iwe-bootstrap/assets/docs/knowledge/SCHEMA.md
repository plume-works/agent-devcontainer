# Frontmatter reference

The human-readable companion to the machine schemas. Validation lives in
`.iwe/schemas/*.yaml`, bound to key globs in `.iwe/config.toml` (`[schemas]`
section) — bindings are by path, and **every** document under `data/` is bound,
hubs included. Run `iwe schema validate` before committing — exit 0 is the gate.

The examples below describe one fictional product (Pomodux, a focus-timer app);
the `*.example.md` docs demonstrate each shape in place.

`data/` is a conformant [Open Knowledge
Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
v0.2 bundle. That is why every document carries a `type` and why the reserved
`data/index.md` has a shape of its own. The per-type blocks below show only the
fields specific to that type; the shared families come next.

## Fields every type carries

OKF's optional families (SPEC §4.1, §5), declared on every schema and checked by
`.iwe/schemas/okf.yaml`:

- `description` — one sentence. Every document has one; it is what an OKF
  consumer and `data/index.md` show before opening the file.
- `sources` — the materials a document derives from, each
  `{ id, resource, title, author, usage_count, last_modified }` with `resource`
  required. A `resource` may be a URL or a repo path. Attribute individual
  claims with a markdown footnote keyed to an entry's `id`.
- `resource`, `tags`, `stale_after`, `usage_window` — optional.

`stage` is the only lifecycle field: the per-type enums below. A work item's
state lives only in its own frontmatter; no hub section repeats it. OKF's
optional `status` is never set, so a state change edits one field. Nor are OKF's
`generated` and `verified`: source control records when and by whom a document
changed.

## The build order — `rank`

Active plans, pending and planned bugs, and pending backlog tasks may carry
`rank`, a positive integer: their place in one build order shared across the
three types, lower first.

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

## The reserved file — `data/index.md`

An OKF reserved filename, not a concept document: it carries no `type` and is
checked by `okf-index.yaml` instead. Its only frontmatter is
`okf_version: "0.2"`. The body is `#` sections of link bullets, each bullet a
markdown link to a hub followed by `-` and that hub's `description`. The graph
holds no `data/log.md`, which OKF makes optional.

## The archive — `data/archive/<release>/<folder>/`

Finished work is archived, never deleted. `data/archive/` holds one folder per
cut version plus `next-release`, and each holds the subfolder its documents
lived in — `plans/`, `bugs/`, `backlog/`, `features/`, or `architecture/` — so
every archived document stays bound to its type's schema and is validated in
full.

- Whoever closes a plan, bug, task, or feature moves it with `iwe rename` to
  `data/archive/next-release/<folder>/` in the same change and removes its hub
  link.
- The release cut moves everything under `next-release` to the version's folder,
  keeping the subfolders.
- The folder is the only record of a document's release; no document carries
  `released`. A document no plan closed belongs to the release that was open
  when it closed.
- `type: architecture` is valid only under `data/archive/`.

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

`release` lists the documents the plan closes: the `features/` and `bugs/` keys
Ship marks implemented or done when the plan ships, or `internal` when it closes
none. It feeds no release page. A plan needs no feature to change what users
see: the release page is written from the specs.

Body: `## Context`, `## Approach`, `## Implementation Steps` (`### Task N`,
`**Files:**`, checkboxes), `## Spec changes`, `## Depends on` (optional),
`## Verification`, `## Out of scope`, `## Key references` (anchors, never line
numbers). Ship moves a done or cancelled plan to the archive and removes its
link from `data/plans.md`. Every plan `## Depends on` links is a prerequisite,
unless the section's text starts with `None`: then it has none, and any plan it
links is only related.

## Features — `data/features/<slug>.md`

A feature is a proposal: what users should get, written before the work. It is
live at `proposed` or `accepted`; once its plan ships, the behaviour lives in
the specs and the feature moves to the archive.

``` yaml
---
type: feature # required
stage: accepted # proposed | accepted live; implemented | deprecated | cancelled archived — required
---
```

Body: `## Purpose`, `## Behaviour`, `## Edge cases`, `## Open questions`. Plan
sets a feature its plan lists in `release` to `accepted`; Ship sets it to
`implemented` and archives it with the plan.

## Bugs — `data/bugs/<slug>.md`

Bug reports and investigations. H1 starts with `Bug:`.

``` yaml
---
type: bug # required
stage: pending # pending | planned | done | cancelled — required
severity: high # critical | high | medium | low — required
---
```

- `stage`: Capture files a bug at `pending`, or at `done` when the same change
  fixed it. Plan moves a bug its plan lists in `release` to `planned`; Ship
  moves it to `done`, and returns it to `pending` when it cancels the plan.
- `severity`: the impact of the defect — how bad it is when it happens — not its
  urgency. Descriptive only; it does not set `rank`.

Body: `## Symptom`, `## Reproduction`, `## Root cause`, all required, then the
optional `## Potential solution` — the intended direction, at any stage — and
`## Fix` — the fix that shipped, written when the bug becomes `done`: by the
fixer when a change fixes it directly, by Ship from the plan that fixed it. A
done or cancelled bug moves to the archive in the same change. A Reproduction or
Root cause not yet known records what is known, the hypotheses eliminated and
what eliminated them, and links the backlog task whose spike settles it. No
section states lifecycle; `stage` does.

## Releases — `data/releases/<version>.md`

One page per cut version, written only by the release cut, in plain text with no
Markdown link.

``` yaml
---
type: release # required
version: 0.1.0 # required
date: 2026-07-18 # the day the release was cut
stage: released # required, always released
---
```

Body: what changed in the requirements and scenarios of `data/spec/` between the
commit that added the previous release page and the cut, in plain language,
grouped by theme; `## Removed` for behaviour that went away; `## Upgrade notes`
when a change needs action; and `## Fixed`, the titles of the bugs in the
release's archive folder. A `## Rationale` change alone is not a release change.
Nothing edits a page after its cut.

## Backlog tasks — `data/backlog/<slug>.md`

Atomic prioritized work items waiting to become plans.

``` yaml
---
type: task # required
stage: pending # pending | done | cancelled — required
priority: high # high | medium | low
created: 2026-08-01 # required, YYYY-MM-DD
completed: 2026-08-14 # set when done
---
```

A done or cancelled task moves to the archive in the same change.

## Reference documents — type only

`data/spec/`, `data/findings/`, `data/guides/`, `data/concept/`, and
`data/someday/` docs carry a `type` (`spec`, `finding`, `guide`, `concept`,
`someday`) and nothing else that is required: they are durable reference, not
work items, so no `stage` applies, and the finding and guide schemas reject one.

- **Spec** — the only home of behaviour: `### Requirement:` + SHALL,
  `#### Scenario:` + WHEN/THEN. Its `## Rationale` section is the only home of
  the decision in force behind that behaviour and the alternatives it rejected;
  it states no behaviour.
- **Finding** — a measurement: required `## Measurement` and `## Closing`, plus
  the hypotheses eliminated and what would settle the rest. It states no
  behaviour the code must meet.
- **Guide** — a procedure a contributor follows. Every code anchor in it is
  resolved on every commit.

## Hubs and the trackers

Hub files (`data/plans.md`, `data/features.md`, …) carry `type: hub`;
`data/product.md` and `data/milestone.md` carry `type: tracker`. Both take
`stage: living`. A hub's body is one flat list of inclusion links, one per
member, sorted by the member's key with any `YYYYMMDD-` prefix removed, with no
`##` sections — `.iwe/schemas/hub.yaml` rejects a section, and a test checks the
order. A hub changes only when a member is created, removed, or renamed.
