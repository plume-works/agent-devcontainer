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
- Delete `.github/pull_request_template.md`. Rejected: the text box of the
  GitHub web interface then opens empty, and a person finds nothing that tells
  where the structure is.
- A symbolic link from the template to the skill. Rejected: no tool reads the
  template, because `pr-open` always gives the body through
  `gh pr create --body-file`. The structure is a section list in the `SKILL.md`
  of `pr-gen-description`, not a separate file. Also, this repository keeps no
  symbolic links.

## Consequences

- `pr-gen-description` owns the structure and never reads a structure from the
  template. The stub holds `<!-- pr-gen-description: no-template -->` and no
  section headings, so it cannot become different from the skill.
- When a pull request template has section headings, the skill does not use it
  and tells the caller so. The skill never ignores such a template without a
  report.
- The guidance can add to a section or change how the skill writes it. It cannot
  merge or rename `## Verification` and `## Reviewer Handoff`, because the tense
  split is the one rule that guidance cannot change.
- A pull request description is on GitHub and not in the repository, so no
  automatic check can examine its format. Only the skills that write it and the
  reviewers that read it keep the format.
