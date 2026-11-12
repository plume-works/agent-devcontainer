---
type: task
description: Move a consumer workspace bootstrapped from the earlier iwe-bootstrap scaffold to the single-home layout — findings, guides, the archive, plain-text release pages, and no architecture type, released field, or data/log.md.
stage: pending
priority: medium
created: 2026-11-12
sources:
- resource: .agents/plugins/agentdev/skills/iwe-bootstrap/assets/
- resource: docs/knowledge/CHANGELOG.md
- resource: docs/knowledge/data/plans/20261112-knowledge-base-single-home.md
---

# Migrate a repository that consumed the earlier IWE scaffold

A repository that ran `/agentdev:iwe-bootstrap` before the single-home layout
holds `data/architecture/`, `data/log.md`, the `okf-log` schema, `released`
fields on done plans, release pages that link features, and closed plans, bugs,
tasks, and features listed in their hubs. The current scaffold and the workflow
rulebooks write the new layout, so once such a consumer updates the catalog its
graph is checked against rules it does not meet.

The work: give that consumer a migration path —

- copy the new `.iwe/` bindings and schemas: `finding`, `guide`, the archive
  globs, and no `okf-log`;
- add the findings and guides hubs;
- fold each architecture note into the owning spec's `## Rationale`, a finding,
  or a guide;
- move each closed document to `data/archive/<release>/<folder>/` by the release
  that took it, and drop `released`;
- replace each release-page link with its text, and delete `data/log.md`.

Whether this is a script, a `template-consume` update step, or written steps in
the Migration section of `docs/knowledge/CHANGELOG.md` is for the plan to
decide.
