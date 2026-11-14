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
- A failed bootstrap, an incorrect setting, a failed core phase, or a core
  service with no recovery budget left latches the runtime. With
  `AGENTDEV_STRICT_STARTUP=true`, a failed optional service also latches it.
- A latch stops OpenCode, also when OpenCode is the failed service, because a
  service whose probes used all of its budget can continue to run. Nothing
  restarts, and the runtime does not become ready again.
- `agentdev-runtime supervisor retry` continues from the failed component in the
  same container. Before supervisord starts, PID 1 itself waits for the retry
  and runs the configuration check and the bootstrap again.
- The bootstrap runs in its own process session. PID 1 stops a failed bootstrap
  together with each process that it started, so no part of it runs at the same
  time as the retry.
- PID 1 parses `ENABLE_FIREWALL` and gives the firewall exactly `true` or
  `false`. A value that the firewall does not know latches the runtime and does
  not leave egress open.
- Each failure writes the command, the exit status, and the end of the output of
  the failed attempt to `last-failure.json` on the home volume. A failure before
  the home volume is ready goes only to stderr.
