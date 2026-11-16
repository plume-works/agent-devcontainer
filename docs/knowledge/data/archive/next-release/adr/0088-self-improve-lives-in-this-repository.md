---
type: adr
stage: deprecated
description: The self-improve plugin is in this repository next to agentdev, and the runtime installs and enables it with each other plugin that the marketplace publishes.
---

# The self-improve plugin is in this repository

The `self-improve` loop changes the skills, agents, and instructions that this
repository supplies. As a result, the loop and the catalog are in one
repository, and `.claude-plugin/marketplace.json` publishes `self-improve` next
to `agentdev`. The loop also needs a permanent destination for each lesson, and
this repository has typed destinations and skills that write to them.

## Considered Options

- A separate repository for the loop, which uses the catalog. Rejected: each
  repository then has its own lint, CI, lock file, and tool versions, and they
  must agree.
- A copy of the loop as a subtree that nobody owns. Rejected: this repository
  develops the loop and does not only carry it.

## Consequences

- The committed `.claude/settings.json` does not enable `self-improve`.
- Some tests of `self-improve` start real Claude sessions and use the model.
  They run only when `SELF_IMPROVE_RUN_LIVE` is set. A marker filter in
  `addopts` does not prevent the run, because a test path or `-m` replaces it.
