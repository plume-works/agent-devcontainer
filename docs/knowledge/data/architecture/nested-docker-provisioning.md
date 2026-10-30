---
type: architecture
description: The agentdev-devcontainer runtime supervises the nested dockerd instead of the Docker-in-Docker feature, on a per-container /var/lib/docker volume, and SSH comes from the sshd feature plus image-level packages, so the same image works from a Codespace.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-29T21:00:00Z
sources:
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: .devcontainer/scripts/runtime-docker.sh
- resource: .devcontainer/devcontainer.json
- resource: .devcontainer/devcontainer-lock.json
- resource: .devcontainer/devcontainer-init.sh
- resource: ansible/roles/basic_prereqs/tasks/main.yml
- resource: https://github.com/Dr-QP/Dr.QP/pull/406
- resource: https://github.com/Dr-QP/Dr.QP/pull/407
- resource: https://github.com/Dr-QP/Dr.QP/pull/403
---

# Nested Docker provisioning

## Decision

The nested Docker engine is a supervised service of the `agentdev-devcontainer`
runtime: `runtime-docker.sh run` starts `dockerd`, and the runtime controller
gates readiness on it and recovers it within its budget. The image's Dev
Container metadata mounts a per-container volume at `/var/lib/docker`.

SSH is provided by the `devcontainers/features/sshd` feature, while the packages
it needs (`openssh-server`, `rsync`) are installed in the image by Ansible.

## Why the runtime owns the engine

A nested `dockerd` cannot use the container's own overlay-mounted writable layer
for `/var/lib/docker`, so the engine needs a separate mount and someone has to
start, watch, and restart it. The runtime already supervises every other service
the editor relies on, with readiness and bounded recovery; the engine joins that
graph, and `runtime-docker.sh` refuses to start without the separate mount.

The upstream `ghcr.io/devcontainers/features/docker-in-docker` feature was the
previous provider. Keeping it beside the supervised engine was rejected because
two components would then start and restart one daemon, so exactly one owns it.
The same supervised engine serves the deploy image, which has no Dev Containers
client to run a feature (see [Dev Container runtime](devcontainer-runtime.md)).

## Why the SSH capability is split across a feature and the image

The feature performs sshd **configuration**; the image supplies the
**packages**. Installing the packages at image build time keeps a Codespace
usable immediately rather than paying an apt install on every container create;
keeping configuration in the feature avoids reimplementing host-key and account
setup.

This split is what makes the image reachable over `gh codespace ssh`, which the
`/agentdev:remote-codespace-session` skill depends on as its transport when no
Docker daemon is available locally.

## The host-side precondition

`devcontainer-init.sh` runs on the **host**, before the container is built, and
Codespaces invokes it through `/bin/sh -c` with no `HOME` set. Every expansion
of `$HOME` there must be guarded. An unguarded reference aborts the whole build
and drops the user into a recovery container rather than failing with a legible
error.

## Consequences

- Upgrading Docker is an image change; upgrading SSH configuration is a feature
  version bump in `devcontainer.json` plus a regenerated
  `devcontainer-lock.json`.
- The sshd feature runs at container-create time, so it takes effect even before
  a rebuilt image carries the packages.
