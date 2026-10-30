---
type: plan
created: 2026-10-13
release:
- features/shared-buildkit-builder
description: Run one BuildKit daemon in a dedicated Coder workspace and make it the default builder for docker build inside every Dev Container, falling back to the local builder when it is unreachable.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T16:18:33Z
sources:
- resource: .devcontainer/scripts/coder-agent-start.sh
- resource: docs/knowledge/data/plans/20261029-off-bash-migration.md
- resource: https://github.com/plume-works/coder-ide-baseline/blob/ff4e472/template/main.tf
- resource: https://docs.docker.com/build/builders/drivers/remote/
- resource: https://docs.docker.com/build/cache/garbage-collection/
---

# Share one BuildKit builder across Coder workspaces

## Context

Each Coder workspace's Dev Container engine keeps its own BuildKit cache, so
workspaces that build the same images each store and rebuild the same layers.
[Cap Docker storage with automatic garbage
collection](20261013-docker-storage-gc.md) bounds each cache. This plan removes
the duplication: workspaces share one builder and one cache.

The Coder agent start this plan extends is `agentdev-runtime coder start`, which
[Replace the runtime shell scripts with one agentdev-runtime
CLI](20261029-off-bash-migration.md) ports from `coder-agent-start.sh`. The
builder registration is written into that command, never as a new script under
`.devcontainer/scripts/`, which that plan removes.

## Approach

One `buildkitd` runs in a dedicated, always-on Coder workspace, with its state
in a persistent volume. Each Dev Container's agent start registers it as a
`remote`-driver buildx builder named `shared`, with `default-load=true` so a
plain `docker build` still loads its result into the local engine. The agent
start makes `shared` the default builder when it answers, and selects the local
`default` builder otherwise. A builder that becomes unreachable mid-session
fails the build; `docker build --builder default` builds locally.

The registration is `agentdev-runtime docker builder`, beside the existing
`docker run` and `docker prune`. `coder start` runs it the way it runs prune and
the credential helper: a failure is a warning, and Remote Control still starts.

Only `docker build` inside Dev Containers changes. The devcontainer CLI builds
the Dev Container image on the workspace engine, which keeps its own builder.

Decided by the maintainer: the daemon runs in a dedicated Coder workspace, not
as a host service, and it is the default builder, not opt-in.

Still open, settled by Task 1 before anything is built:

- how a Dev Container reaches the builder workspace — for example
  `coder port-forward` to a loopback port, which needs a Coder user session, or
  a published port reached over the host network;
- how the endpoint is authenticated. `buildkitd` over TCP accepts any client
  unless mTLS is configured, so an endpoint reachable from outside Coder
  workspaces needs mTLS;
- the builder workspace's template: a second template in
  `plume-works/coder-ide-baseline`, or `coder-ide-baseline` with a parameter.

Assumption: the shared cache keeps at most 30 GB, set in the builder's
`buildkitd.toml`; change it in Task 2 if Task 1 finds a reason.

Rejected: a host service next to Sysbox, by maintainer decision; it would
survive any workspace, but needs host access to deploy and change.

## Implementation Steps

### Task 1: Decide transport, authentication, and template shape

**Files:** Create:
`docs/knowledge/data/architecture/shared-buildkit-workspace.md`

- [ ] Write the architecture document: the chosen transport, how the endpoint is
  authenticated, where the builder workspace's template lives, and the rejected
  alternatives.
- [ ] Probe the chosen transport from a Dev Container in a live workspace and
  record the result under `## Verification results`.

### Task 2: Template the builder workspace

**Files:** per Task 1, in `plume-works/coder-ide-baseline`

- [ ] The template runs `buildkitd` with its state in a per-workspace persistent
  volume, garbage collection capped at 30 GB, and the endpoint and
  authentication from Task 1.
- [ ] Open the pull request, with `terraform fmt -check` and
  `terraform validate` passing.

### Task 3: Start the builder workspace

**Files:** none (live Coder deployment)

- [ ] After the Task 2 pull request merges and its version is pushed, create the
  builder workspace, set it to never auto-stop, and record its name under
  `## Verification results`.

### Task 4: Register the shared builder on agent start

**Files:** Create: `py_packages/agentdev_runtime/tests/test_docker_builder.py`;
Modify: `py_packages/agentdev_runtime/agentdev_runtime/docker.py`,
`py_packages/agentdev_runtime/agentdev_runtime/coder.py`,
`scripts/tests/test_coder_agent_start.py`

- [ ] `agentdev-runtime docker builder` creates or updates the `shared` builder
  with the `remote` driver, the Task 1 endpoint, and `default-load=true`. It
  runs `docker buildx use shared` when
  `docker buildx inspect --bootstrap shared` succeeds within a timeout, and
  `docker buildx use default` otherwise. It exits 0 in every case, and does
  nothing when `docker` or buildx is missing. Tests cover reachable,
  unreachable, and missing-tool paths with a stub `docker`.
- [ ] `agentdev-runtime coder start` runs it before the Remote Control start,
  and its failure is a warning that does not stop Remote Control from starting.
  Tests cover the failure path.

### Task 5: Confirm the shared cache across workspaces

**Files:** none (live workspaces)

- [ ] Build the same Dockerfile with plain `docker build` in two workspaces and
  record under `## Verification results` that the second build reuses cached
  layers.
- [ ] Record under `## Verification results` that the second build's image is in
  that workspace's local engine.
- [ ] Stop the builder workspace, restart a workspace's agent, and record under
  `## Verification results` that a third build runs on the local builder.

## Spec changes

New spec `spec/shared-buildkit`. Changing every Dev Container's default builder
is behavior other workflows rely on, so it carries a full delta.

``` markdown
## ADDED Requirements (spec/shared-buildkit)

### Requirement: Dev Containers build on the shared builder when it answers

`agentdev-runtime coder start` SHALL register a buildx builder named `shared`,
using the `remote` driver with `default-load=true`, pointed at the builder
workspace. It SHALL make `shared` the default builder when the builder answers
within a timeout, and SHALL select the local `default` builder otherwise. The
agent start SHALL continue when registration fails.

#### Scenario: the builder workspace is running

- **WHEN** the agent starts and the shared builder answers
- **THEN** `docker build` in the Dev Container runs on the shared builder and
  loads the result into the Dev Container engine.

#### Scenario: the builder workspace is stopped

- **WHEN** the agent starts and the shared builder does not answer
- **THEN** the local `default` builder is selected and the agent start
  continues.

#### Scenario: two workspaces build the same layers

- **WHEN** a second workspace builds layers the first already built on the
  shared builder
- **THEN** the second build reuses them from the shared cache.

### Requirement: the shared builder bounds its cache

The builder workspace SHALL keep its BuildKit state in a persistent volume, with
garbage collection limiting the cache to 30 GB.

#### Scenario: the builder workspace restarts

- **WHEN** the builder workspace restarts
- **THEN** its build cache is still there.
```

## Depends on

[Replace the runtime shell scripts with one agentdev-runtime
CLI](20261029-off-bash-migration.md)

## Verification

- `uv run pytest py_packages/agentdev_runtime/tests/test_docker_builder.py scripts/tests/test_coder_agent_start.py`
- `uv run ruff check py_packages/agentdev_runtime`
- `terraform fmt -check` and `terraform validate` for the builder template.
- Task 5's live cross-workspace checks.

## Out of scope

- Builds the devcontainer CLI runs on the workspace engine.
- Sharing images or registry pulls between workspaces.
- Builder isolation between Coder users; the deployment has one user.
- Codespaces and local Dev Containers, which have no Coder agent start.

## Key references

Verified anchor points (line numbers as of 2026-10-30). The runtime CLI plan
ports `coder-agent-start.sh` to `agentdev-runtime coder start` and the Docker
scripts to `agentdev_runtime/docker.py`.

- `.devcontainer/scripts/coder-agent-start.sh:13` — credential helper call, a
  warning on failure; `:21` — `exec` of `claude-remote-control-start.sh`
- `scripts/tests/test_coder_agent_start.py:70` —
  `test_remote_control_starts_when_helper_setup_fails`
- `.devcontainer/scripts/runtime-supervisor.py:309` — `dockerd`, the Dev
  Container engine whose builder changes
- `coder-ide-baseline` `template/main.tf:113` — `coder_agent.dev`; `:259` —
  `coder_script.agent_start`; `:435` — `docker_container.workspace`
