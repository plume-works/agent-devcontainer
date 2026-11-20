---
type: adr
stage: accepted
description: The runtime supervises the nested Docker engine on a volume of its own in both runtime profiles, and the image has no SSH server.
---

# The runtime supervises the Dev Container engine, and the image has no SSH server

A nested Docker engine cannot use the overlay-mounted writable layer of the
container for `/var/lib/docker`. As a result, it needs a separate volume and an
owner that starts, watches, and restarts it. The runtime already supervises
every other service that the editor relies on, so the engine is a supervised
service of the runtime in both runtime profiles: the runtime gates readiness on
it and recovers it within its recovery budget. The same supervised engine serves
the deploy image, which has no Dev Containers client to run a feature.

## Considered Options

- The `ghcr.io/devcontainers/features/docker-in-docker` feature, alone or with
  the supervised engine. Rejected: beside the supervised engine, two components
  would start and restart one daemon. Alone, it cannot serve the deploy image.
- Docker-outside-of-docker in place of a nested engine. Rejected: it breaks bind
  mounts of Dev Container paths outside the repository, which running the tools
  of another image against Dev Container files depends on.

## Consequences

- The Dev Containers client attaches through Docker, and Coder reaches the Dev
  Container as a sub-agent of the Coder agent. No supported host connects to an
  `sshd` in the container, so the image installs no `openssh-server`.
