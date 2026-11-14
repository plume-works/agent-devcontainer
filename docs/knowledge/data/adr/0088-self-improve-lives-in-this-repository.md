---
type: adr
stage: accepted
description: The self-improve plugin lives in this repository beside agentdev, and the runtime installs and enables it with each other plugin that the marketplace publishes.
---

# The self-improve plugin lives in this repository

The `self-improve` loop changes the skills, agents, and instructions that this
repository supplies. As a result, the loop and the catalog are in one
repository, and `.claude-plugin/marketplace.json` publishes `self-improve`
beside `agentdev`.

## Considered Options

- A separate repository for the loop, which uses the catalog. Rejected: each
  repository then has its own lint, CI, lock file, and tool versions, and they
  must agree.
- A copy of the loop as a subtree that nobody owns. Rejected: this repository
  develops the loop and does not only carry it.

## Consequences

- `agentdev-runtime catalog install` installs each plugin that the marketplace
  publishes. The create phase and the attach phase install at user scope, so
  each Dev Container and standalone runtime enables `self-improve` and its
  hooks.
- The committed `.claude/settings.json` does not enable `self-improve`.
