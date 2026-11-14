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

### Requirement: the host-side init runs without HOME

`.devcontainer/devcontainer-init.sh` SHALL complete when the host runs it
through `/bin/sh -c` with `HOME` unset: it SHALL NOT expand `$HOME` without a
default.

#### Scenario: Codespaces runs the initialize command

- **WHEN** the initialize command runs with no `HOME` in its environment
- **THEN** the script writes `.devcontainer/.env` and exits 0, and the build
  continues.
