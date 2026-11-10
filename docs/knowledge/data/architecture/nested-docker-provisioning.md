---
type: architecture
description: The agentdev-devcontainer runtime supervises the nested dockerd instead of the Docker-in-Docker feature, on a per-container /var/lib/docker volume, and the container runs no SSH server.
sources:
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: py_packages/agentdev_runtime/agentdev_runtime/docker.py
- resource: .devcontainer/devcontainer.json
- resource: .devcontainer/devcontainer-init.sh
- resource: ansible/roles/basic_prereqs/tasks/main.yml
- resource: https://github.com/Dr-QP/Dr.QP/pull/406
- resource: https://github.com/Dr-QP/Dr.QP/pull/407
- resource: https://github.com/Dr-QP/Dr.QP/pull/403
---

# Nested Docker provisioning

## Decision

The nested Docker engine is a supervised service of the `agentdev-devcontainer`
runtime: `agentdev-runtime docker run` starts `dockerd`, and the runtime
controller gates readiness on it and recovers it within its budget. The image's
Dev Container metadata mounts a per-container volume at `/var/lib/docker`.

The container runs no SSH server: the descriptor declares no Dev Container
feature and the image installs no `openssh-server`.

## Why the runtime owns the engine

A nested `dockerd` cannot use the container's own overlay-mounted writable layer
for `/var/lib/docker`, so the engine needs a separate mount and someone has to
start, watch, and restart it. The runtime already supervises every other service
the editor relies on, with readiness and bounded recovery; the engine joins that
graph, and `agentdev-runtime docker` refuses to start without the separate
mount.

The upstream `ghcr.io/devcontainers/features/docker-in-docker` feature was the
previous provider. Keeping it beside the supervised engine was rejected because
two components would then start and restart one daemon, so exactly one owns it.
The same supervised engine serves the deploy image, which has no Dev Containers
client to run a feature (see [Dev Container
runtime](../../../../openspec/specs/agentdev-runtime-images/spec.md#rationale)).

## Why there is no SSH server

Editors and terminals reach the container through their host's own channel: the
Dev Containers client attaches through Docker, and Coder exposes the Dev
Container as a sub-agent that `coder ssh <workspace>.repo` reaches through the
Coder agent (see spec/coder-ide-baseline). No supported host connects to an
in-container `sshd`, so the image carries none (human:author).

## The host-side precondition

`devcontainer-init.sh` runs on the **host**, before the container is built, and
Codespaces invokes it through `/bin/sh -c` with no `HOME` set. Every expansion
of `$HOME` there must be guarded. An unguarded reference aborts the whole build
and drops the user into a recovery container rather than failing with a legible
error.

## Consequences

- Upgrading Docker is an image change.
