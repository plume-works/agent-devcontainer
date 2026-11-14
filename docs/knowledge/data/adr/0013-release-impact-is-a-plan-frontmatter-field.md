---
type: adr
stage: accepted
description: The release impact of a plan is its required release frontmatter field, set when the plan is written.
---

# The release impact of a plan is a frontmatter field

The maintainer decided that the author of a plan sets its release impact when
they write the plan, and that the plan review examines it. It is the `release`
frontmatter field, because `.iwe/schemas/plan.yaml` can require a frontmatter
field only on an active plan. The value is `internal`, or the keys of the
features and bugs that the plan closes.

## Considered Options

- A `## Release` body section. Rejected: the schema cannot require a body
  section only on an active plan, so only the skills can make sure of it.
