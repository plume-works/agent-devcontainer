---
type: adr
stage: accepted
---

# PID 1 runs the create phase, and the image label declares the lifecycle commands

The create phase needs what `agentdev-runtime bootstrap` prepares as root: the
runtime account's sudoers entry, its home, and the shared auth directory. For
this reason, PID 1 runs it as the supervised one-shot `created` program after
the bootstrap, as the standalone runtime's `prepare` program does, and
`postCreateCommand` only waits for it. Work whose timing PID 1 cannot observe
stays in three thin lifecycle commands. The `devcontainer.metadata` label of
`agentdev-devcontainer` declares them, so every descriptor that selects the
image inherits them.

## Consequences

- A descriptor that also declares the lifecycle commands runs each command
  twice.
- The label mounts a volume for each container at `/var/lib/docker`, because the
  Dev Container engine refuses the overlay file system of the container.
