---
type: task
stage: done
priority: medium
created: 2026-11-09
description: Give architecture notes a lifecycle, so a note a newer decision replaces is retired instead of staying listed as current.
sources:
- resource: docs/knowledge/AGENTS.md
- resource: .iwe/schemas/architecture.yaml
- resource: docs/knowledge/data/archive/3.0.0/architecture/label-review-triggers.md
- resource: docs/knowledge/data/archive/2.0.0/architecture/assignee-review-trigger.md
- resource: docs/knowledge/data/archive/2.0.0/architecture/pr-review-effort-tiers.md
completed: 2026-11-12
---

# Give architecture notes a lifecycle

A new architecture note can replace an earlier decision, but nothing in the
graph retires the earlier note. It stays listed in `data/architecture.md` beside
its successor and reads as current to anyone who lands on it.
`architecture/label-review-triggers` ends with "This supersedes" and links
`architecture/assignee-review-trigger` and
`architecture/pr-review-effort-tiers`, while both of those still describe their
mechanisms as in force and link nowhere forward.

Three rules combine to produce this:

- `AGENTS.md#project-memory › "References point newer to older"` and the rule
  that the document a finding came from is not edited. The planner applies them
  to a replaced decision too, so only the new note links the old one.
- `.iwe/schemas/architecture.yaml` gives an architecture note no `stage` or
  other retirement field, and `docs/knowledge/AGENTS.md` lists end states for
  plans, bugs, tasks, and features, but none for an architecture note.
- Ship merges spec deltas into specs, and no Ship step touches an architecture
  note, so a plan that replaces a decision updates the specs and leaves the old
  note as it was.

`architecture/assignee-review-trigger` carries `stage: superseded` as a stopgap
marker; the schema does not define that value.

Decide how a replaced architecture note ends, and make the planner and the
Shipper carry it out:

- **Remove it.** Repoint every link to the successor (`iwe` can rewrite them)
  and delete the note; git history keeps its text. About ten documents link
  `assignee-review-trigger` today, including closed plans and `log.md`.
- **Mark it.** Add `superseded` as an architecture `stage` in the schema and
  `SCHEMA.md`, with a link to the successor, and keep it listed.

Then add the step to the `iwe-planner` rulebook, which names the note a plan
replaces, and to the `iwe-shipper` rulebook, which retires it at Ship, and apply
the decision to `assignee-review-trigger` and `pr-review-effort-tiers`.
