---
type: adr
stage: accepted
description: An unrecoverable failure latches the runtime; a standalone runtime waits until an operator tells it to try again, and a Dev Container exits.
---

# A latch waits for a retry in the standalone runtime and ends a Dev Container

When the `controller` event listener cannot recover a core service, it latches
the runtime. In the standalone runtime profile, PID 1 and supervisord continue
to run until an operator runs `agentdev-runtime supervisor retry`. PID 1 exits
nonzero only when the `controller` event listener or supervisord fails, which
leaves the container's restart policy for crashes. In the Dev Container profile,
PID 1 exits, because an editor has no retry command, and a container that keeps
running with its readiness withdrawn looks attached and healthy.

## Considered Options

- Exit PID 1 nonzero on each unrecoverable failure in the standalone runtime.
  Rejected: under the Compose policy `restart: unless-stopped`, the container
  then reruns its non-transactional preparation steps against the same volumes
  without bound.
