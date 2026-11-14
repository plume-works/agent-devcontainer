---
type: adr
stage: accepted
description: PID 1 runs the create phase as a supervised one-shot program, and the image label declares the three Dev Container lifecycle commands.
---

# PID 1 runs the create phase, and the image label declares the lifecycle commands

The create phase needs the sudoers entry, the home, and the shared auth
directory that the root bootstrap prepares. For this reason, PID 1 runs it as
the `created` program after the root bootstrap, and `postCreateCommand` only
waits for it. Work whose time PID 1 cannot see stays in three small lifecycle
commands. The `devcontainer.metadata` label of `agentdev-devcontainer` declares
them, so each descriptor that selects the image gets them.

## Consequences

- A descriptor that also declares the lifecycle commands runs each command two
  times.
