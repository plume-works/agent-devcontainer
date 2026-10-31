---
type: someday
description: When a standalone-runtime dependency such as D-Bus recovers, stop its dependents first and restart them in order, verifying a real client operation.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T04:39:39Z
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/supervisor.py
---

# Dependency-ordered service recovery

The standalone runtime's controller restarts a failed dependency but leaves its
dependents running. A keyring or Xpra attached to a dead D-Bus, or OpenCode
attached to a replaced CBM daemon, can pass its shallow probe while its
connection is broken.

The idea: on a dependency failure, stop its transitive dependents in reverse
order, recover the dependency, start the dependents in order, and keep readiness
withdrawn throughout. Then confirm with a real client operation, such as storing
and reading a secret, rather than process or HTTP liveness.

Held back because it moves the controller toward a general init system. The
current `refresh` list restarts the known clients of D-Bus and CBM, which covers
the dependencies that exist today.
