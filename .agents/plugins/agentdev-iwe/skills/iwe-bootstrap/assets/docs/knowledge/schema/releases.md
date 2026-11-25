# Releases

A release page says what one cut version changed. Only the release cut writes
it, and nothing edits it after the cut.

- Path: `data/releases/<version>.md`. The version is a semantic version.
- Hub: `data/releases.md`.

``` yaml
---
type: release # required
version: 0.1.0 # required
date: 2026-07-18 # the day the release was cut
stage: released # required, always released
---
```

Body: plain text with no Markdown link, with these sections in this order. A
page leaves out a section that has no content.

- Sections with a theme as the heading — in plain language, the changes that the
  `## Acceptance` scenarios of the plans in the archive folder of the release
  state. For an archived plan with no `## Acceptance`, the page uses its
  `## Spec changes`.
- `## Removed` — behaviour that went away.
- `## Upgrade notes` — a change that needs action from a consumer.
- `## Decisions` — the title of each ADR that became accepted or superseded
  after the commit that added the previous release page.
- `## Fixed` — the title of each bug in the archive folder of the release.
