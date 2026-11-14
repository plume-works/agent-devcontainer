---
type: adr
stage: accepted
description: Each uses reference to an action or reusable workflow of this repository starts with $/, and the zizmor self-repository audit enforces it.
---

# Local actions use the self-repository syntax

A `uses:` value in the self-repository syntax loads the action from the commit
that runs, so a step needs no earlier checkout. GitHub records the reference as
pinned, so a full-SHA pin policy covers each action. For this reason, each
reference to an action or reusable workflow of this repository starts with `$/`.

## Considered Options

- Keep `./` and stop the zizmor audit. Rejected: each local action then needs an
  earlier checkout, and the pin policy cannot apply.
- `owner/repo/path@sha` references. Rejected: the reference pins a commit that
  is not the one that runs, so an action and its caller cannot change together.

## Consequences

- A step cannot load an action that an earlier step wrote to disk.
- The action content is the same as with `./`. The change does not repair a
  security problem.
- A job runs `actions/checkout` only when a step reads the working tree.
- A consumer whose runners do not support `$/` must change these workflows
  before it can use them.
