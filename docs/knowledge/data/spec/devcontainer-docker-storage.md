---
type: spec
description: The agentdev-devcontainer image supervises its nested Docker engine on persistent non-overlay storage, caps its BuildKit cache at 10 GB, and collects its garbage hourly, removing unused images older than 72 hours, unshared build cache over 10 GB, and old unused disposable volumes.
sources:
- resource: ansible/roles/install_docker/tasks/main.yml
- resource: py_packages/agentdev_runtime/agentdev_runtime/docker.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/coder.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/supervisor.py
- resource: scripts/tests/test_docker_gc.py
- resource: scripts/tests/test_coder_agent_start.py
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: docker/devcontainer/supervisord.conf
---

# Devcontainer Docker storage

The Dev Container engine is the nested `dockerd` that `agentdev-devcontainer`
supervises ([nested Docker
provisioning](../../../../openspec/specs/devcontainer-docker-storage/spec.md#rationale)).
It holds the images and build cache of work done inside the Dev Container. The
workspace engine around it is bounded by the `coder-ide-baseline` template's
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
`(^|_)dind-var-lib-(docker|containerd)-` or `_agentdev-(cache|codex)$`, and that
was created more than 72 hours ago. A pass SHALL NOT remove any other volume. A
failed step SHALL only warn, the pass SHALL continue with the next step, and a
pass SHALL always exit successfully.

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
