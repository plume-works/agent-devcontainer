---
type: bug
stage: done
severity: high
description: Coder workspaces that run for days pile up unused Docker images, build cache, and volumes despite the storage limits of spec/devcontainer-docker-storage and spec/coder-ide-baseline, because the image prune runs only at agent start and only on images older than 72 hours, the build-cache cap cannot free cache that kept images share, and nothing removes volumes.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/docker.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/coder.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/supervisor.py
- resource: ansible/roles/install_docker/tasks/main.yml
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: .devcontainer/docker-compose.yml
- resource: openspec/specs/devcontainer-docker-storage/spec.md
- resource: openspec/specs/coder-ide-baseline/spec.md
- resource: docs/knowledge/data/features/docker-storage-limits.md
- resource: https://github.com/plume-works/coder-ide-baseline/blob/4a2d980/template/main.tf
- resource: https://github.com/plume-works/coder-ide-baseline/blob/4a2d980/root-container/daemon.json
---

# Bug: Docker storage accumulates on long-running Coder workspaces

## Symptom

[Docker storage limits](../features/docker-storage-limits.md) promises that both
engines of a Coder workspace bound their storage so workspaces sharing one host
disk do not fill it. On 2026-11-01, five workspaces on one host held about 263
GB that no container used:

- The Dev Container engine of `agent-dev1` held 61 images (59 GB), with no
  container running, 42 GB of build cache, and 65 volumes. 58 of those volumes
  were `dind-var-lib-docker-<id>`.
- The workspace engines held 18–27 GB of build cache each, against a configured
  10 GB cap.
- On the workspace engines, Dev Container volumes that the current descriptor no
  longer mounts held up to 16 GB per workspace.

## Reproduction

1. Run a Coder workspace from `coder-ide-baseline` with no autostop, which is
   the template's default, for several days.
2. Build images in the Dev Container, and bring up Dev Containers under new ids,
   for example from new worktrees or test runs.
3. Run `docker system df` in both engines. Images younger than 72 hours stay
   until the next agent start, the build cache exceeds 10 GB, and every
   `dind-var-lib-docker-<id>` volume of a removed Dev Container remains.

## Root cause

Each of the three gaps lets one kind of storage grow:

- **The image prune runs only at agent start.**
  - Both engines run `docker image prune -af --filter until=72h` once, when an
    agent starts. The workspace engine runs it from the template's `coder_agent`
    startup script. The Dev Container engine runs it from
    `agentdev-runtime coder start` and from the supervisor's one-shot `prune`
    service after `dockerd`.
  - The template sets no autostop, so a workspace that runs for days never
    prunes again.
  - `until` compares creation time, so even a prune on every start keeps
    everything built in the last 72 hours.
- **The 10 GB build-cache cap cannot reach shared cache.**
  - Both engines set `builder.gc.defaultMaxUsedSpace` to `10GB`.
  - With the containerd image store, build cache and image layers share
    snapshots. On `agent-dev1`, only 7.9 GB of the 42 GB of build cache was
    reclaimable, and after the unused images were removed,
    `docker builder prune -af` freed the rest.
  - Not ruled out: BuildKit may enforce the cap only after a build, never on a
    timer. A `docker system df` reading before and after an idle period with no
    builds would settle it.
- **Nothing removes volumes.**
  - Neither spec covers volumes.
  - The image's devcontainer metadata gives each Dev Container a
    `dind-var-lib-docker-${devcontainerId}` volume. Every new id adds one, and
    removing the Dev Container leaves it behind.
  - A descriptor change also orphans volumes: `agentdev-cache` and
    `dind-var-lib-containerd-<id>` are no longer mounted by
    `.devcontainer/docker-compose.yml` or the image.
  - Volumes that hold logins (`agentdev-agents-auth`, `*_agentdev-claude`,
    `*_agentdev-opencode`) must survive a cleanup even when no container uses
    them. So a blanket `docker volume prune -a` is not a safe fix.

## Potential solution

A one-off cleanup reclaims the space but does not stop it building up again. A
fix needs:

- a prune that runs periodically while a workspace is up, not only at agent
  start;
- a rule for volumes, such as removing unused `dind-var-lib-*` volumes and
  volumes the current descriptor does not mount, while keeping login volumes by
  name;
- a decision on the 72-hour window;
- updates to `spec/devcontainer-docker-storage` and `spec/coder-ide-baseline`,
  which define today's start-only prune.

Reaching the template half needs a change in `plume-works/coder-ide-baseline`.

## Fix

[Collect Docker garbage hourly in both workspace
engines](../plans/20261101-docker-storage-periodic-gc.md) replaced the
start-only prune with an hourly pass in each engine: the Dev Container's
supervised `docker-gc` service and the workspace engine's `docker-gc.timer`
(plume-works/coder-ide-baseline#32). A pass removes unused images created more
than 72 hours ago, trims the build cache no kept image shares to 10 GB, and
removes unused volumes with disposable names created more than 72 hours ago.

## Key references

- `py_packages/agentdev_runtime/agentdev_runtime/docker.py::PREFIX` —
  `PRUNE_AGE`; `py_packages/agentdev_runtime/agentdev_runtime/docker.py::run` —
  `prune`; `py_packages/agentdev_runtime/agentdev_runtime/docker.py::_docker` —
  the `docker image prune -af --filter until=72h` call
- `py_packages/agentdev_runtime/agentdev_runtime/coder.py::STEPS` — `STEPS`,
  which runs the prune once per agent start
- `py_packages/agentdev_runtime/agentdev_runtime/supervisor.py::DEPLOY_SERVICES`
  — the one-shot `prune` service after `dockerd`
- `ansible/roles/install_docker/tasks/main.yml › "defaultMaxUsedSpace"` — the
  Dev Container engine's `defaultMaxUsedSpace` of `10GB`
- `docker/devcontainer/agentdev-devcontainer.Dockerfile › "dind-var-lib-docker-${devcontainerId}"`
  — the `dind-var-lib-docker-${devcontainerId}` volume mount
- `docs/knowledge/data/spec/devcontainer-docker-storage.md#requirement-the-dev-container-engine-limits-its-build-cache`
  — Requirement: the Dev Container engine limits its build cache;
  `docs/knowledge/data/spec/devcontainer-docker-storage.md#requirement-the-agent-start-prunes-unused-dev-container-images`
  — Requirement: the agent start prunes unused Dev Container images
- `docs/knowledge/data/spec/coder-ide-baseline.md#requirement-the-workspace-engine-bounds-its-own-storage`
  — Requirement: the workspace engine bounds its own storage
- `plume-works/coder-ide-baseline@4a2d980` `template/main.tf` — the startup
  script's image prune; `root-container/daemon.json` — the workspace engine's
  `defaultMaxUsedSpace`
