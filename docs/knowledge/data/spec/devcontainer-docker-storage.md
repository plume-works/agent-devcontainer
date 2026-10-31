---
type: spec
description: The agentdev-devcontainer image supervises its nested Docker engine on persistent non-overlay storage, caps its BuildKit cache at 10 GB, and the Coder agent start prunes its unused images older than 72 hours.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T20:55:00Z
sources:
- resource: ansible/roles/install_docker/tasks/main.yml
- resource: py_packages/agentdev_runtime/agentdev_runtime/docker.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/coder.py
- resource: scripts/tests/test_docker_image_prune.py
- resource: scripts/tests/test_coder_agent_start.py
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: docker/devcontainer/supervisord.conf
---

# Devcontainer Docker storage

The Dev Container engine is the nested `dockerd` that `agentdev-devcontainer`
supervises ([nested Docker
provisioning](../architecture/nested-docker-provisioning.md)). It holds the
images and build cache of work done inside the Dev Container. The workspace
engine around it is bounded by the [Coder IDE baseline
template](coder-ide-baseline.md).

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
10 GB build-cache limit, and the supervised daemon SHALL run with it.

#### Scenario: the build cache passes the limit

- **WHEN** builds inside the Dev Container push the build cache past 10 GB
- **THEN** BuildKit garbage collection reduces it to at most 10 GB.

### Requirement: the agent start prunes unused Dev Container images

`agentdev-runtime coder start` SHALL run `agentdev-runtime docker prune`, which
removes images in the Dev Container engine that no container references and that
were created more than 72 hours ago. The prune SHALL NOT prevent the rest of the
agent start, including Remote Control.

#### Scenario: Docker is unavailable

- **WHEN** `docker` is missing or its daemon does not answer
- **THEN** the command prunes nothing and exits successfully.

#### Scenario: the prune fails

- **WHEN** `docker image prune` exits non-zero
- **THEN** the command warns and exits successfully, and Remote Control still
  starts.

#### Scenario: an image is in use

- **WHEN** an image older than 72 hours is referenced by a running or stopped
  container
- **THEN** it is kept.
