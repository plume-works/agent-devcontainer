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
- The `created` program starts after the root bootstrap and the keyring, and
  readiness waits for it.
- `postCreateCommand` runs `agentdev-runtime lifecycle created --wait`, which
  fails when the runtime fails. `postStartCommand` runs
  `agentdev-runtime lifecycle ready` at each start, and it is the `waitFor`
  target. `postAttachCommand` runs `agentdev-runtime lifecycle attached` at each
  attach. As a result, the editor never attaches to a container whose core
  services failed.
- The label also sets `overrideCommand: false`, so the client keeps the
  entrypoint. It sets `DEV_WORKSPACE_FOLDER`, so PID 1 and the create phase know
  the workspace folder of the editor. It mounts a volume for each container at
  `/var/lib/docker`, because the nested engine refuses the overlay file system
  of the container.
