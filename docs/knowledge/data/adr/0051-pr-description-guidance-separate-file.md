---
type: adr
stage: accepted
description: Pull request description guidance of a consumer lives in .github/pr-description-guidance.md as instructions, and the pull request template stays a two-state pointer.
---

# Pull request description guidance is a separate file

`.github/pull_request_template.md` is only one of two states: the stub or a real
template. As a result, a template update can identify the state. The guidance of
a consumer is in `.github/pr-description-guidance.md`. The consumer owns this
file, and updates keep it. The guidance holds instructions, because
`pr-gen-description` owns the list of sections.

## Considered Options

- A guidance block in the pull request template. Rejected: the template is then
  not a two-state pointer, and an update must merge consumer text into a
  template path.
- A list of section headings. Rejected: it is a structure file with a different
  name, and the section list of `pr-gen-description` replaces it.
