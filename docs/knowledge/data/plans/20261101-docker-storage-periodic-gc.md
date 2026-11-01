---
type: plan
created: 2026-11-01
release:
- bugs/coder-docker-storage-accumulates
- features/docker-storage-limits
description: Replace the start-only image prune in both Docker engines of a Coder workspace with an hourly garbage collection that also trims the build cache to its 10 GB cap and removes old, unused, disposable volumes.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T21:45:00Z
sources:
- resource: docs/knowledge/data/bugs/coder-docker-storage-accumulates.md
- resource: py_packages/agentdev_runtime/agentdev_runtime/docker.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/coder.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/supervisor.py
- resource: docker/devcontainer/supervisord.conf
- resource: docker/deploy/supervisord.conf
- resource: https://github.com/plume-works/coder-ide-baseline/blob/4a2d980/template/main.tf
- resource: https://github.com/plume-works/coder-ide-baseline/blob/4a2d980/root-container/Dockerfile
---

# Collect Docker garbage hourly in both workspace engines

## Context

[Bug: Docker storage accumulates on long-running Coder
workspaces](../bugs/coder-docker-storage-accumulates.md) found three gaps in the
storage limits of [Docker storage limits](../features/docker-storage-limits.md):

- Each engine prunes images only when an agent starts, and workspaces have no
  autostop.
- The 10 GB BuildKit cap does not free cache that kept images share.
- Nothing removes volumes.

The Dev Container engine's limits are specified in [Devcontainer Docker
storage](../spec/devcontainer-docker-storage.md), the workspace engine's in
[Coder IDE baseline](../spec/coder-ide-baseline.md), and the deploy image's in
[Standalone OpenCode runtime](../spec/standalone-opencode-runtime.md).

## Approach

The maintainer chose the following:

- **Cadence:** each engine runs a garbage-collection pass hourly, and the first
  pass runs when the engine's host starts. That first pass replaces today's
  start-only prune.

- **Images:** keep today's rule. Each pass runs
  `docker image prune -af --filter until=72h`.

- **Build cache:** each pass then runs
  `docker builder prune -f --max-used-space 10GB`, so the cap holds even when no
  build runs.

- **Volumes:** an allow-list, gated by age. A pass removes a volume only when
  all three hold:

  - no container, running or stopped, references it;
  - its name matches a disposable pattern;
  - it was created more than 72 hours ago.

  The disposable patterns are the nested engine's storage and volumes no current
  descriptor mounts:

  ``` text
  (^|_)dind-var-lib-(docker|containerd)-
  _agentdev-(cache|codex)$
  ```

  Every other volume, including `agentdev-agents-auth` and the
  `_agentdev-claude` and `_agentdev-opencode` volumes, is never touched.

Each step of a pass is independent: a failure warns, the pass continues, and the
pass always exits 0.

**The Dev Container and deploy images.**

- `agentdev-runtime docker gc` runs one pass.
- `agentdev-runtime docker gc --every` runs a pass, then repeats it every
  `AGENTDEV_DOCKER_GC_INTERVAL` seconds (default `3600`).
- A non-core supervised `docker-gc` service, ordered after `dockerd`, runs the
  repeating form in both profiles. In the deploy profile it replaces the
  one-shot `prune` service.
- `agentdev-runtime coder start` drops its prune step, since the service's first
  pass covers the start.
- `agentdev-runtime docker prune` is removed.

**The workspace engine.**

- `coder-ide-baseline`'s `root-container` image gains a
  `/usr/local/bin/docker-gc` script with the same three steps.
- A systemd `docker-gc.service` runs the script, and a `docker-gc.timer` fires
  it 15 minutes after boot and then hourly.
- The template's startup script drops its own prune line.

**Assumptions:**

- The Dev Container engine's collection now runs wherever the image runs,
  Codespaces and local Dev Containers included, not only on Coder. Its rules are
  the ones the start-time prune already applied on Coder.
- The workspace engine cannot run `agentdev-runtime`, because its image comes
  from another repository. Its script therefore restates the three steps in
  shell, with the same patterns and limits.

**Rejected alternatives:**

- A keep-list volume rule, which removes every unused volume except named login
  volumes. It deletes any new stateful volume whose container happens to be gone
  at the time.
- A blanket `docker volume prune -a`. It deletes logins on any engine with no
  containers.
- Relying on BuildKit's own GC for the cache. It cannot free cache that kept
  images share, and may only run after a build.
- Turning on Coder autostop so that the start-time prune runs. That changes how
  workspaces behave to work around the cleanup's schedule.

## Implementation Steps

### Task 1: One garbage-collection pass

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/docker.py`,
`py_packages/agentdev_runtime/agentdev_runtime/cli.py`; Create:
`scripts/tests/test_docker_gc.py`; Delete:
`scripts/tests/test_docker_image_prune.py`

- [ ] `agentdev-runtime docker gc` runs
  `docker image prune -af --filter until=72h`, then
  `docker builder prune -f --max-used-space 10GB`, then removes each dangling
  volume whose name matches a disposable pattern and whose `CreatedAt` is more
  than 72 hours old. `docker prune` is gone. Tests with a stub `docker` cover
  the command order. For volumes, they check that an old disposable volume is
  removed, a young disposable volume is kept, and an old login volume is kept.
- [ ] Docker missing or its daemon unreachable: the pass does nothing and exits
  0\. A failing step warns, the remaining steps still run, and the pass exits 0.
  Tests cover each case.

### Task 2: The repeating form

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/docker.py`,
`py_packages/agentdev_runtime/agentdev_runtime/settings.py`,
`py_packages/agentdev_runtime/README.md`; Modify:
`scripts/tests/test_docker_gc.py`

- [ ] `agentdev-runtime docker gc --every` runs a pass at once, then one every
  `AGENTDEV_DOCKER_GC_INTERVAL` seconds. The variable is parsed in `settings`
  with default `3600` and listed in the package README. A test with a short
  interval sees at least two passes.

### Task 3: Supervise the collector in both images

**Files:** Modify:
`py_packages/agentdev_runtime/agentdev_runtime/supervisor.py`,
`docker/devcontainer/supervisord.conf`, `docker/deploy/supervisord.conf`,
`scripts/tests/test_agent_runtime_docker.py`

- [ ] Both profiles carry a non-core `docker-gc` service after `dockerd`, backed
  by a `program:docker-gc` that runs `agentdev-runtime docker gc --every`. The
  deploy profile's `prune` service and `program:prune` are removed. The test
  that checked `program:prune` checks `program:docker-gc` in both images, and a
  failing collector does not latch the runtime.

### Task 4: Drop the prune from the Coder agent start

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/coder.py`,
`scripts/tests/test_coder_agent_start.py`

- [ ] `agentdev-runtime coder start` runs the credential helper and the OpenCode
  start, then Remote Control, with no Docker step. Tests assert the new step
  list.

### Task 5: The workspace engine's collector

**Files (plume-works/coder-ide-baseline):** Create: `root-container/docker-gc`,
`root-container/docker-gc.service`, `root-container/docker-gc.timer`; Modify:
`root-container/Dockerfile`, `template/main.tf`, `README.md`

- [ ] The `root-container` image installs `/usr/local/bin/docker-gc`, which runs
  the three steps with Task 1's patterns and limits, warning on any failed step
  and exiting 0. It also installs and enables `docker-gc.timer`, which runs it
  15 minutes after boot and then hourly. The template's startup script no longer
  prunes, and the README describes the hourly collection.

### Task 6: Template version activated on Coder

- [ ] A `coder-ide-baseline` template version carrying Task 5 is pushed and
  active.

### Task 7: CI green on the pull request

- [ ] The pull request's image builds and runtime acceptance pass, both images
  included.

### Task 8: Both collectors run on a live workspace

- [ ] On a Coder workspace updated to the Task 6 version and the new Dev
  Container image, `systemctl list-timers docker-gc.timer` shows the timer in
  the workspace engine. The Dev Container's `docker-gc` service logs a pass at
  start, and another an interval later.

## Spec changes

[Devcontainer Docker storage](../spec/devcontainer-docker-storage.md):

``` markdown
## MODIFIED Requirements

### Requirement: the Dev Container engine limits its build cache

The image's Docker configuration SHALL enable BuildKit garbage collection with a
10 GB build-cache limit, and the supervised daemon SHALL run with it. Each
garbage-collection pass SHALL also trim the build cache to at most 10 GB.

#### Scenario: the build cache passes the limit

- **WHEN** builds inside the Dev Container push the build cache past 10 GB
- **THEN** BuildKit garbage collection reduces it to at most 10 GB.

#### Scenario: the cache stays over the limit without a build

- **WHEN** the build cache is over 10 GB and no build runs
- **THEN** the next garbage-collection pass reduces it to at most 10 GB.

## REMOVED Requirements

### Requirement: the agent start prunes unused Dev Container images

Retired: the supervised hourly garbage collection replaces the prune at Coder
agent start, whose single run left workspaces that never restart unpruned.

## ADDED Requirements

### Requirement: the Dev Container engine collects garbage hourly

Both runtime profiles SHALL supervise a non-core `docker-gc` service after
`dockerd` that runs `agentdev-runtime docker gc --every`. It SHALL run one pass
when it starts and another every `AGENTDEV_DOCKER_GC_INTERVAL` seconds, default
3600. A pass SHALL remove images no container references that were created more
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
```

[Coder IDE baseline](../spec/coder-ide-baseline.md):

``` markdown
## MODIFIED Requirements

### Requirement: the workspace engine bounds its own storage

The workspace engine SHALL run with BuildKit garbage collection enabled and a 10
GB build-cache limit, from `/etc/docker/daemon.json` in the base image. A
systemd `docker-gc.timer` in the base image SHALL run `/usr/local/bin/docker-gc`
15 minutes after boot and then hourly. Each run SHALL apply the
garbage-collection pass of
[Devcontainer Docker storage](devcontainer-docker-storage.md) to the workspace
engine, with the same image age, build-cache limit, and volume patterns. A
failed step SHALL only warn. The template's startup script SHALL NOT prune.

#### Scenario: a stopped Dev Container's image survives the collection

- **WHEN** the Dev Container is stopped and the collector runs
- **THEN** the Dev Container's image is kept, because its stopped container
  references it.

#### Scenario: the workspace runs for days

- **WHEN** a workspace stays up for longer than 72 hours
- **THEN** unused images, build cache over 10 GB, and old unused disposable
  volumes are removed within an hour of qualifying, without a restart.
```

[Standalone OpenCode runtime](../spec/standalone-opencode-runtime.md):

``` markdown
## MODIFIED Requirements

### Requirement: nested Docker and opt-in firewall retain their policies

The runtime SHALL operate its own persisted DinD engine through a private Unix
socket, without a host socket mount or Docker TCP listener. It SHALL retain 10
GB BuildKit GC and the hourly garbage collection of
[Devcontainer Docker storage](devcontainer-docker-storage.md), with every
collection error nonfatal. The egress firewall SHALL remain opt-in; enabled
configuration SHALL retain its allowlist/IPv6 policy and self-checks while
supporting explicitly trusted proxy ingress and nested Docker operation.

#### Scenario: the engine restarts

- **WHEN** the container or nested daemon is replaced using its persistent
  storage
- **THEN** its existing images remain available and builds run as the runtime
  user.

#### Scenario: the firewall is enabled

- **WHEN** a valid allowlist and trusted proxy sources are configured
- **THEN** required proxy access and nested builds work, forbidden egress
  remains blocked, and daemon network rules are not erased by startup ordering.
```

## Verification

- `uv run pytest scripts/tests/test_docker_gc.py scripts/tests/test_coder_agent_start.py scripts/tests/test_agent_runtime_docker.py`
- `grep -rn "docker prune\|program:prune" py_packages docker scripts` finds
  nothing.
- In `coder-ide-baseline`: `shellcheck root-container/docker-gc`, and the
  `root-container` image builds in its CI.
- On a live workspace: Task 8's checks, plus `docker system df` in both engines
  showing build cache at or under 10 GB an hour after a build pushed it over.

## Out of scope

- Changing the 72-hour image window, or counting it from last use.
- Removing the per-id `dind-var-lib-docker-<id>` volumes from test runs as they
  finish. The age-gated collection removes them three days later.
- Coder autostop for workspaces.
- Host-level deduplication ([someday](../someday/host-filesystem-dedup.md)).

## Key references

Verified anchor points (line numbers as of 2026-11-01):

- `py_packages/agentdev_runtime/agentdev_runtime/docker.py:23` — `PRUNE_AGE`;
  `:113` — `prune`; `:138` — `main`
- `py_packages/agentdev_runtime/agentdev_runtime/cli.py:141` — the `docker`
  command entry
- `py_packages/agentdev_runtime/agentdev_runtime/coder.py:15` — `STEPS`
- `py_packages/agentdev_runtime/agentdev_runtime/settings.py:190` — the
  `Variable` table entry pattern; `:350` — `positive`
- `py_packages/agentdev_runtime/agentdev_runtime/supervisor.py:210` —
  `DEPLOY_SERVICES`; `:219` — the `prune` service; `:227` —
  `DEVCONTAINER_SERVICES`
- `docker/deploy/supervisord.conf:115` — `program:prune`
- `docker/devcontainer/supervisord.conf:37` — `program:dockerd`
- `scripts/tests/test_agent_runtime_docker.py:136` —
  `test_the_image_prune_runs_once_the_nested_engine_is_up`
- `scripts/tests/test_coder_agent_start.py:9` — `IMAGE_PRUNE`
- `plume-works/coder-ide-baseline@4a2d980` `template/main.tf:146` — the startup
  script's prune; `root-container/Dockerfile:47` — `systemctl enable docker`;
  `:50` — the `daemon.json` copy
