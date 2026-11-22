---
type: adr
stage: accepted
---

# Pull request description guidance is a separate file

`.github/pull_request_template.md` stays a pure two-state pointer, the stub or a
real template, so a template update can tell the two apart. The guidance of a
consumer is in `.github/pr-description-guidance.md`, consumer-created state that
updates preserve. The guidance holds instructions, because `pr-gen-description`
owns the section list: a section such as `## Rollback plan` is captured as an
instruction to cover rollback.

## Considered Options

- A guidance block in the pull request template. Rejected: the template would
  stop being a two-state pointer, and an update would have to merge consumer
  text into a template path.
- Delete `.github/pull_request_template.md`. Rejected: the text box of the
  GitHub web interface would open blank, and a person arriving at the repository
  would find nothing pointing at where the description structure lives. A stub
  that names no sections avoids both and cannot drift, because it makes no
  structural claim.
