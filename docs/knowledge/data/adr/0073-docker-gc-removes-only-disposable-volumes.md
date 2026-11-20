---
type: adr
stage: accepted
description: A supervised service collects Docker garbage when it starts and then each hour, and it removes only old disposable volumes.
---

# Docker garbage collection is a supervised hourly service with an allow-list for volumes

All Coder workspaces share one host disk. A full disk stops a workspace from
unpacking its Dev Container image, so its sub-agent never starts and nothing
that the Coder agent start runs, Remote Control included, comes up. Workspaces
have no autostop, so a prune at agent start almost never runs. As a result, the
supervised `docker-gc` service runs a garbage collection pass when it starts and
then each hour.

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
- The cache limit counts only cache that no image kept by the pass shares.
  Shared cache is the layers of such an image, so removing it frees no disk; it
  starts to count once a pass removes its image.
- A pass removes a volume only when it is old and its name matches
  `py_packages/agentdev_runtime/agentdev_runtime/docker.py::DISPOSABLE_VOLUME`,
  so a volume that the pass does not know is kept. Per-id test volumes are left
  to that age limit rather than removed as each run finishes.
