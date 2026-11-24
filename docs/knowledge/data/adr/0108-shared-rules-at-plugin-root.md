---
type: adr
stage: proposed
---

# Shared rules live at the plugin root; output formats stay in the skill

Rules that more than one skill or agent applies live once, in
`rules/<artifact>.md` at the root of the plugin that ships them. A rulebook is
concise and instructional, and names no skill; each skill that uses one says
how. A skill's output format is prescriptive and private to that skill, in its
`references/reporting.md`. A skill that reads another's output reads it free
form, so it handles a person's comment as well as a skill's. The maintainer made
this decision.

## Considered Options

- The rulebook in the writer skill's `references/rules.md`, read by the reviewer
  through a link into that skill. Rejected: a skill can write one artifact and
  review another, and some writers are agents, so a rulebook has no single
  owning skill.
- A rulebook in the writer skill where one exists, and at the plugin root
  otherwise. Rejected: two places to look.
- A fixed comment format that the reader parses. Rejected: comments also come
  from people, in any form.

## Consequences

- A rulebook is shared only within one plugin: a link to another plugin's
  `rules/` breaks once the plugins install separately.
