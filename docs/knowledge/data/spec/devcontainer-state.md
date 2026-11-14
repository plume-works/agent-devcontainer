---
type: spec
description: Where the Dev Container keeps state — Claude credentials on an auth volume the host init creates per host UID and GID, everything else on a per-instance home volume that starts empty and the bootstrap claims for the remapped account, each checkout's .venv linked to its own environment on that volume, and root-only tests run through a launcher.
sources:
- resource: .devcontainer/devcontainer-init.sh
- resource: .devcontainer/docker-compose.yml
- resource: .devcontainer/devcontainer.json
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: docker/base/agentdev-base.Dockerfile
- resource: py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/project.py
- resource: .pre-commit-config.yaml
- resource: scripts/run-root-tests
- resource: scripts/tests/conftest.py
- resource: scripts/tests/scratch.py
- resource: .github/workflows/ci.yml
---

# Dev Container state

## Purpose

Defines where the Dev Container keeps the state that outlives a rebuild and how
it is prepared for the non-root runtime account. Which state is shared across
instances, and the per-checkout environment rule, belong to `catalog-lifecycle`
and `agentdev-runtime-images`; this spec holds the volumes' creation and
preparation, the `.venv` link's edge cases, and the root-test launcher.

## Requirements

### Requirement: the create phase re-owns the sibling checkout volume

The create phase SHALL re-own `/workspaces/project` recursively to the account
when it is a mount the account does not own, unless it is the open workspace
folder or the account is root.

#### Scenario: a sibling checkout volume from an earlier identity

- **WHEN** the create phase runs and `/workspaces/project` is a mount owned by
  another UID
- **THEN** it is re-owned to the account, and its uncommitted work stays
  editable
