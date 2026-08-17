---
type: task
description: Write a capture skill that creates the three inbox lanes — backlog tasks, bugs, and proposed features — which AGENTS.md step 4 specifies but no skill writes.
stage: planned
priority: medium
created: 2026-08-15
generated:
  by: claude-code/opus-5
  at: 2026-08-15T00:00:00Z
sources:
- resource: .claude/skills/explore/SKILL.md
- resource: docs/knowledge/AGENTS.md
- resource: docs/knowledge/SCHEMA.md
---

# Write a capture skill

The operating loop's Record step (`AGENTS.md`) specifies three inbox lanes that
no skill creates: `data/backlog/<slug>.md`, `data/bugs/<slug>.md`, and
`proposed`-stage `data/features/<slug>.md`. Every other lane has an owner —
`plan` writes plans, `ship` writes specs, implemented features, releases, and
the log, and `explore` captures someday, architecture, and concept docs.

The three orphans share one shape: write a single document with type-specific
frontmatter, add an inclusion link to the right hub section, then
`iwe normalize` and `iwe schema validate`. That is one skill, not three —
mirroring how `explore`'s Capturing section already covers its own three lanes
as a group.

Scope to settle when this becomes a plan: whether `proposed` features belong
here or with a design-first flow of their own; and whether capture should also
own the `someday` → `backlog` promotion that `someday.md` describes but leaves
unowned.

The lanes are cheap to write by hand, which is the argument against the skill —
but the frontmatter is schema-enforced per `SCHEMA.md`, and the hub link is easy
to forget, which is the argument for it. Decide at planning time.

This item was itself filed by hand, for want of the skill it describes.
