---
type: adr
stage: accepted
description: The standalone runtime calls the same agentdev_runtime functions as the Dev Container lifecycle commands, not the lifecycle commands themselves.
---

# The standalone runtime shares functions, not lifecycle commands

`agentdev-deploy` installs `agentdev_runtime` and calls the same functions that
the Dev Container lifecycle commands call. Each path that the functions use has
a setting, with the Dev Container layout as the default.
`AGENTDEV_RUNTIME_MODE=deploy` makes a step fail where the Dev Container
lifecycle writes a log entry and continues.

## Considered Options

- Run the lifecycle commands without change. Rejected: they need root, a
  checkout that holds the setup files of this repository, and the call order of
  the Dev Containers client.
- Copy all of the checkout into the image. Rejected: it has the same needs.

## Consequences

- The catalog stays the staged catalog. A checkout that holds a complete catalog
  replaces it for that start.
