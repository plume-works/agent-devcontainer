---
type: adr
stage: accepted
description: An unrecoverable failure latches the runtime; a deploy container waits for an explicit retry, and a Dev Container exits.
---

# A latch waits for a retry in deploy and ends a Dev Container

When the controller cannot recover a core service, it latches the runtime. In
the deploy profile, PID 1 and supervisord continue to run until an operator runs
`agentdev-runtime supervisor retry`. PID 1 exits nonzero only when the
controller or supervisord fails. In the Dev Container profile, PID 1 exits,
because an editor has no retry command. A container that continues to run but is
not ready looks attached and serviceable.

## Considered Options

- Exit PID 1 nonzero on each unrecoverable failure in deploy. Rejected: under
  the Compose policy `restart: unless-stopped`, the container then runs the
  preparation steps again on the same volumes without a limit. These steps are
  not transactional.

## Consequences

- `agentdev_runtime.supervisor::Profile` sets `exit_on_latch` only for the
  `devcontainer` profile.
