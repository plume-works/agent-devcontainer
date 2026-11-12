---
type: spec
description: The agentdev-devcontainer image supervises its nested Docker engine on a per-container non-overlay volume, runs no SSH server, caps its BuildKit cache at 10 GB, and collects its garbage hourly, removing unused images older than 72 hours, unshared build cache over 10 GB, and old unused disposable volumes.
sources:
- resource: ansible/roles/install_docker/tasks/main.yml
- resource: py_packages/agentdev_runtime/agentdev_runtime/docker.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/coder.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/supervisor.py
- resource: scripts/tests/test_docker_gc.py
- resource: scripts/tests/test_coder_agent_start.py
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: docker/devcontainer/supervisord.conf
- resource: docker/deploy/supervisord.conf
- resource: scripts/tests/test_agent_runtime_docker.py
- resource: .devcontainer/devcontainer.json
- resource: .devcontainer/devcontainer-init.sh
---

# Devcontainer Docker storage

The Dev Container engine is the nested `dockerd` that `agentdev-devcontainer`
supervises. It holds the images and build cache of work done inside the Dev
Container. The workspace engine around it is bounded by the `coder-ide-baseline`
template's
[`spec/workspace-template`](https://github.com/plume-works/coder-ide-baseline/blob/main/docs/knowledge/data/spec/workspace-template.md).

## Requirements

### Requirement: the Dev Container image supervises its nested Docker engine

`agentdev-devcontainer` SHALL run the nested Docker daemon through its managed
service profile on non-overlay persistent storage and SHALL apply the image's
BuildKit garbage-collection policy.

#### Scenario: Docker becomes ready

- **WHEN** the Dev Container runtime starts
- **THEN** runtime readiness remains blocked until the managed Docker daemon
  answers its probe.

#### Scenario: Docker exhausts recovery

- **WHEN** the daemon cannot recover within its bounded budget
- **THEN** the runtime fails and reports Docker as the terminal service.

### Requirement: the engine runs on a per-container volume, with no SSH server

The image's Dev Container metadata SHALL mount a per-container volume
`dind-var-lib-docker-${devcontainerId}` at `/var/lib/docker`, and
`agentdev-runtime docker run` SHALL refuse to start `dockerd` when its data
directory is on the container's overlay filesystem. Both runtime profiles SHALL
start the engine through `agentdev-runtime docker run` under the supervisor. The
repository's Dev Container descriptor SHALL declare no Dev Container feature,
and the image SHALL install no `openssh-server`.

#### Scenario: the data directory is on the overlay

- **WHEN** `agentdev-runtime docker run` finds `/var/lib/docker` on `overlayfs`
- **THEN** it exits non-zero naming the overlay filesystem, and `dockerd` does
  not start.

#### Scenario: the deploy image starts

- **WHEN** the deploy image's supervisor starts
- **THEN** it runs the same supervised `dockerd` as the Dev Container image.

### Requirement: the host-side init runs without HOME

`.devcontainer/devcontainer-init.sh` SHALL complete when the host runs it
through `/bin/sh -c` with `HOME` unset: it SHALL NOT expand `$HOME` without a
default.

#### Scenario: Codespaces runs the initialize command

- **WHEN** the initialize command runs with no `HOME` in its environment
- **THEN** the script writes `.devcontainer/.env` and exits 0, and the build
  continues.

### Requirement: the Dev Container engine limits its build cache

The image's Docker configuration SHALL enable BuildKit garbage collection with a
10 GB build-cache limit, and the supervised daemon SHALL run with it. Each
garbage-collection pass SHALL also trim the build cache that no kept image
shares to at most 10 GB, and SHALL leave cache that a kept image shares.

#### Scenario: the build cache passes the limit

- **WHEN** builds inside the Dev Container push the build cache past 10 GB
- **THEN** BuildKit garbage collection reduces it to at most 10 GB.

#### Scenario: the cache stays over the limit without a build

- **WHEN** the build cache is over 10 GB and no build runs
- **THEN** the next garbage-collection pass reduces it to at most 10 GB.

#### Scenario: a kept image shares build cache

- **WHEN** build cache holds layers of an image the pass keeps
- **THEN** the pass keeps that cache until the image is removed.

### Requirement: the Dev Container engine collects garbage hourly

Both runtime profiles SHALL supervise a non-core `docker-gc` service after
`dockerd` that runs `agentdev-runtime docker gc --every`. It SHALL run one pass
when it starts and another every `AGENTDEV_DOCKER_GC_INTERVAL` seconds, default
3600\. A pass SHALL remove images no container references that were created more
than 72 hours ago, then trim the build cache to at most 10 GB, then remove each
volume that no container references, whose name matches
`(^|_)dind-var-lib-(docker|containerd)-` or `_agentdev-(cache|cbm|codex)$`, and
that was created more than 72 hours ago. A pass SHALL NOT remove any other
volume. A failed step SHALL only warn, the pass SHALL continue with the next
step, and a pass SHALL always exit successfully.

#### Scenario: Docker is unavailable

- **WHEN** `docker` is missing or its daemon does not answer
- **THEN** the pass removes nothing and exits successfully.

#### Scenario: a step fails

- **WHEN** the image prune exits non-zero
- **THEN** the pass warns, still trims the build cache and removes volumes, and
  exits successfully.

#### Scenario: an image is in use

- **WHEN** an image older than 72 hours is referenced by a running or stopped
  container
- **THEN** it is kept.

#### Scenario: an old image was pulled recently

- **WHEN** no container references an image that was built more than 72 hours
  ago and pulled within the last hour
- **THEN** the pass removes it, because the age is the image's creation time,
  not its last pull or use.

#### Scenario: a disposable volume is old and unused

- **WHEN** no container references `dind-var-lib-docker-<id>` and it was created
  more than 72 hours ago
- **THEN** the pass removes it.

#### Scenario: a disposable volume is young

- **WHEN** no container references a `dind-var-lib-docker-<id>` created less
  than 72 hours ago
- **THEN** the pass keeps it.

#### Scenario: a login volume is unused

- **WHEN** no container references `agentdev-agents-auth` or a
  `_agentdev-claude` volume
- **THEN** the pass keeps it, however old it is.

#### Scenario: the collector fails

- **WHEN** the `docker-gc` service exits or fails to start
- **THEN** the runtime does not latch, and every other service keeps running.

## Rationale

### The runtime supervises the nested engine, and the image runs no SSH server

The nested `dockerd` is a supervised service of the `agentdev-devcontainer`
runtime, which gates readiness on it and recovers it within its budget. A nested
engine cannot use the container's overlay-mounted writable layer for
`/var/lib/docker`, so it needs a separate mount and an owner that starts,
watches, and restarts it; the runtime already supervises every other service the
editor relies on. The same supervised engine serves the deploy image, which has
no Dev Containers client to run a feature. Upgrading Docker is an image change.

Editors and terminals reach the container through their host's own channel — the
Dev Containers client attaches through Docker, and Coder reaches the Dev
Container as a sub-agent through the Coder agent — so no supported host connects
to an in-container `sshd`, and the image carries none.

Rejected:

- **The `ghcr.io/devcontainers/features/docker-in-docker` feature, alone or
  beside the supervised engine.** Beside it, two components would start and
  restart one daemon; alone, it cannot serve the deploy image.
- **Docker-outside-of-docker in place of a nested engine.** It breaks bind
  mounts of Dev Container paths outside the repository, which running another
  image's tools against Dev Container files depends on.

### Garbage is collected hourly by a supervised service, with an allow-list for volumes

All Coder workspaces share one host disk, and a full disk stops a workspace from
unpacking its Dev Container image, so its sub-agent never starts and nothing the
agent start runs, Remote Control included, comes up. The 10 GB and 72-hour
values are the maintainer's choice.

Workspaces have no autostop, so a prune at agent start almost never runs; the
collector is a supervised service that runs a pass when the host starts and then
hourly. Each pass runs `docker builder prune` itself because BuildKit's own
garbage collection may run only after a build. The cache limit counts only cache
no kept image shares, which `docker buildx du` reports as Private: shared cache
is a kept image's layers, so removing it frees no disk, and it starts to count
once the 72-hour image rule removes its image. Volumes are removed only when
their name matches a disposable pattern and they are old, so a volume the pass
has never heard of is kept. Per-id `dind-var-lib-docker-<id>` test volumes are
left to that age-gated pass rather than removed as each run finishes.

Rejected:

- **A keep-list that removes every unused volume except named login volumes.**
  It deletes any new stateful volume whose container happens to be gone.
- **A blanket `docker volume prune -a`.** It deletes logins on an engine with no
  containers.
- **Turning on Coder autostop so a start-time prune runs.** It changes workspace
  behaviour to suit a cleanup schedule.
- **Turning off the containerd image store to keep all storage under one
  directory.** Both limits would still be needed, and Docker's default store
  would be given up.
