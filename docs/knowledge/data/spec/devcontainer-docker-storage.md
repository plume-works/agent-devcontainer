---
type: spec
description: The Dev Container's nested Docker engine caps its BuildKit cache at 10 GB, and the Coder agent start prunes its unused images older than 72 hours.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-13T21:30:00Z
sources:
- resource: ansible/roles/install_docker/tasks/main.yml
- resource: .devcontainer/scripts/docker-image-prune.sh
- resource: .devcontainer/scripts/coder-agent-start.sh
- resource: scripts/tests/test_docker_image_prune.py
- resource: scripts/tests/test_coder_agent_start.py
---

# Devcontainer Docker storage

The Dev Container engine is the nested `dockerd` from the [docker-in-docker
feature](../architecture/nested-docker-provisioning.md). It holds the images and
build cache of work done inside the Dev Container. The workspace engine around
it is bounded by the [Coder IDE baseline template](coder-ide-baseline.md).

## Requirements

### Requirement: the Dev Container engine limits its build cache

The image's `/etc/docker/daemon.json` SHALL enable BuildKit garbage collection
with a 10 GB build-cache limit, and the nested `dockerd` SHALL run with it.

#### Scenario: the build cache passes the limit

- **WHEN** builds inside the Dev Container push the build cache past 10 GB
- **THEN** BuildKit garbage collection reduces it to at most 10 GB.

### Requirement: the agent start prunes unused Dev Container images

`coder-agent-start.sh` SHALL run `docker-image-prune.sh`, which removes images
in the Dev Container engine that no container references and that were created
more than 72 hours ago. The prune SHALL NOT prevent the rest of the agent start,
including Remote Control.

#### Scenario: Docker is unavailable

- **WHEN** `docker` is missing or its daemon does not answer
- **THEN** the script prunes nothing and exits successfully.

#### Scenario: the prune fails

- **WHEN** `docker image prune` exits non-zero
- **THEN** the script warns and exits successfully, and Remote Control still
  starts.

#### Scenario: an image is in use

- **WHEN** an image older than 72 hours is referenced by a running or stopped
  container
- **THEN** it is kept.
