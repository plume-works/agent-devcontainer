---
type: adr
stage: accepted
description: A supervised service collects Docker garbage when it starts and then each hour, and it removes only old disposable volumes.
---

# Docker garbage collection is a supervised hourly service with a list of the volumes that it can remove

All Coder workspaces share one host disk. When the disk is full, a workspace
cannot extract its Dev Container image, and nothing that the agent start runs
can start. Workspaces have no autostop, so a prune at agent start almost never
runs. As a result, the supervised `docker-gc` service runs a pass when it starts
and then each hour.

## Considered Options

- A keep-list that removes each unused volume except the named login volumes.
  Rejected: it deletes each new stateful volume whose container is gone.
- `docker volume prune -a`. Rejected: it deletes logins on an engine with no
  containers.
- Coder autostop, so that a prune at start runs. Rejected: it changes the
  workspace behaviour for a cleanup schedule.

## Consequences

- Each pass runs `docker builder prune` itself, because BuildKit can run its own
  collection only after a build.
- The cache limit counts only cache that no kept image shares. Shared cache is
  the layers of a kept image, so its removal gives no free disk space.
- A pass never removes a volume whose name does not match
  `py_packages/agentdev_runtime/agentdev_runtime/docker.py::DISPOSABLE_VOLUME`.
  Test volumes stay until the age limit of a pass removes them.
