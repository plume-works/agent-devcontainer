# Guides

A guide is a procedure that a contributor follows to do one job in the
repository, and that the README does not give.

- Path: `data/guides/<slug>.md`.
- Hub: `data/guides.md`.
- Frontmatter: `type: guide`. The schema does not accept a `stage`.

Body: one H1 and the steps. The anchor check resolves each code anchor in a
guide on each commit.
