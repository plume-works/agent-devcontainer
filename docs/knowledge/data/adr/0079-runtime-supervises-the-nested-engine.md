---
type: adr
stage: accepted
description: The runtime supervises the nested Docker engine on a volume of its own in both runtime profiles, and the image has no SSH server.
---

# The runtime supervises the Dev Container engine, and the image has no SSH server

A nested Docker engine cannot keep `/var/lib/docker` on the overlay layer of the
container. As a result, it needs a separate volume and an owner that starts,
watches, and restarts it. The runtime supervises the engine in both runtime
profiles, because it supervises the other services already. Also, the deploy
image has no Dev Containers client to run a feature.

## Considered Options

- The `ghcr.io/devcontainers/features/docker-in-docker` feature, alone or with
  the supervised engine. Rejected: with it, two components start and restart one
  daemon. Alone, it cannot serve the deploy image.
- Docker-outside-of-docker. Rejected: it breaks bind mounts of Dev Container
  paths outside the repository. The tools of another image use these mounts on
  Dev Container files.

## Consequences

- The image metadata mounts `dind-var-lib-docker-${devcontainerId}` at
  `/var/lib/docker`, and
  `py_packages/agentdev_runtime/agentdev_runtime/docker.py::require_storage`
  refuses a data directory on the overlay filesystem.
- The repository descriptor declares no Dev Container feature. A Docker upgrade
  is an image change.
- The Dev Containers client attaches through Docker, and Coder reaches the Dev
  Container as a sub-agent of the Coder agent. No supported host connects to an
  `sshd` in the container, so the image installs no `openssh-server`.
