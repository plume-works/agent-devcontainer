---
type: plan
created: 2026-10-23
release:
- features/reusable-agentdev-devcontainer
description: Publish the agentdev image family and a self-contained Dev Container runtime that reuses the deploy supervisor without copying lifecycle scripts into consumers.
generated:
  by: codex/gpt-5
  at: 2026-10-23T02:45:00Z
sources:
- resource: docs/user-stories/agent-containers.md
- resource: docs/knowledge/data/plans/20261017-standalone-opencode-container.md
- resource: docker/desktop/agent-desktop.Dockerfile
- resource: docker/opencode/agent-opencode.Dockerfile
- resource: docker/opencode/supervisord.conf
- resource: .devcontainer/devcontainer.json
- resource: .devcontainer/docker-compose.yml
- resource: .devcontainer/scripts/runtime-supervisor.py
- resource: .github/workflows/ci.yml
---

# Publish the reusable agentdev Dev Container image

## Context

[Reusable agentdev Dev Container](../features/reusable-agentdev-devcontainer.md)
defines the runtime boundary described by the container user stories: projects
should consume a development runtime and agent workflow without absorbing its
lifecycle implementation. The current `agent-desktop` image supplies tools and
the staged catalog, while this repository's `.devcontainer/` owns the lifecycle
scripts and every consuming repository must copy them to get equivalent
behaviour.

[Ship a standalone OpenCode
container](20261017-standalone-opencode-container.md) establishes the reusable
runtime primitives, foreground services, readiness probes, and supervisor now
needed by both deployment and Dev Container execution. This plan begins only
after that plan ships and refactors the verified runtime.

The resulting image family is `ubuntu-ansible` → lifecycle-neutral
`agentdev-base` → sibling `agentdev-deploy` and `agentdev-devcontainer` images.
The canonical `agent-desktop` and `agent-opencode` names are renamed rather than
maintained as compatibility aliases; the product records no image-name
compatibility promise. `template-consume` remains the supported full-adoption
path. A later IWE-bootstrap plan will let full and minimal adoption reuse one
knowledge initializer; neither that extraction nor template-consume retirement
belongs here.

## Approach

Parameterize the existing runtime controller around explicit deploy and
devcontainer service profiles. Share service adapters, dependency ordering,
health probes, bounded recovery, and shutdown, while giving each image its own
bootstrap and supervisor configuration. The Dev Container entrypoint owns
persistent services; thin image-provided create, start/readiness, and attach
commands retain lifecycle semantics PID 1 cannot observe.

Publish Dev Container metadata in `agentdev-devcontainer` so direct consumers
inherit stable lifecycle commands and defaults from the image. Keep mounts,
workspace selection, editor customization, and repository hooks in the
repository descriptor. Use ordered hook directories and environment variables as
the supported extension interface; reject derived images overwriting managed
runtime files. Migrate this repository first so its checkout catalog still
overrides the staged catalog on attach, and test a fixture consumer and a
derived image before publishing.

Replace the Docker-in-Docker Feature in the canonical configuration with the
supervised Docker service; exactly one component owns daemon startup and
recovery.

## Implementation Steps

### Task 1: Define the two runtime profiles with failing tests

**Files:** Create: `scripts/tests/test_agent_runtime_profiles.py`; Modify:
`.devcontainer/scripts/runtime-supervisor.py`,
`.devcontainer/scripts/runtime-health.sh`

- [x] Add focused tests that define the shared service set and the distinct
  deploy and devcontainer dependency graphs. Prove deploy still gates OpenCode
  on project preparation, with indexing requested in the background, while
  devcontainer omits automatic OpenCode service startup and publishes readiness
  for editor attachment.
  - **Evidence:** commit 6171b723;
    `uv run pytest scripts/tests/test_agent_runtime_profiles.py scripts/tests/test_agent_runtime_supervision.py`
    — 124 passed.
- [x] Cover invalid profile names, disabled optional services, terminal
  failures, bounded recovery, signal handling, and readiness-file semantics so a
  profile cannot silently degrade into a partially initialized container.
  - **Evidence:** commit 6171b723;
    `uv run pytest scripts/tests/test_agent_runtime_profiles.py scripts/tests/test_agent_runtime_supervision.py`
    — 124 passed.

### Task 2: Refactor the supervisor into shared primitives and image profiles

**Files:** Create: `docker/deploy/supervisord.conf`,
`docker/devcontainer/supervisord.conf`; Modify:
`.devcontainer/scripts/runtime-supervisor.py`,
`.devcontainer/scripts/runtime-bootstrap.sh`,
`.devcontainer/scripts/runtime-workspace.sh`,
`.devcontainer/scripts/runtime-health.sh`,
`.devcontainer/scripts/runtime-docker.sh`,
`.devcontainer/scripts/runtime-keyring.sh`; Delete:
`docker/opencode/supervisord.conf`

- [x] Select an explicit `AGENTDEV_RUNTIME_MODE=deploy|devcontainer` service
  profile without evaluating caller-provided shell commands. Keep common
  dependency, health, recovery, and shutdown logic in one controller.
  - **Evidence:** commits 6171b723, ebcccecf;
    `uv run pytest scripts/tests/test_agent_runtime_profiles.py scripts/tests/test_agent_runtime_supervision.py`
    — 127 passed.
- [x] Split bootstrap responsibilities so deploy may create or validate its
  runtime identity and workspace, while devcontainer accepts the Dev Container
  tool's user and mounted workspace without cloning, recursively changing
  checkout ownership, or requiring deploy-only proxy secrets.
  - **Evidence:** commit ebcccecf;
    `uv run pytest scripts/tests/test_agent_runtime_identity.py scripts/tests/test_agent_runtime_workspace.py scripts/tests/test_agent_runtime_firewall.py`
    — the devcontainer bootstrap, no-clone, and proxy-free firewall tests pass;
    `test_rejects_an_unwritable_checkout_without_changing_ownership` fails on
    this host before and after the change.
- [x] Run Docker, D-Bus, keyring, CBM, and Xpra through the devcontainer profile
  with the same probes and recovery guarantees as deploy. Keep OpenCode Web and
  Claude Remote Control opt-in clients rather than required readiness gates.
  - **Evidence:** commit ebcccecf;
    `uv run pytest scripts/tests/test_agent_runtime_profiles.py` — 26 passed,
    including the shared program definitions and per-service recovery and exit.

### Task 3: Package stable Dev Container lifecycle entry points

**Files:** Create: `.devcontainer/scripts/devcontainer-created.sh`,
`.devcontainer/scripts/devcontainer-ready.sh`,
`.devcontainer/scripts/devcontainer-attached.sh`,
`.devcontainer/scripts/run-agentdev-hooks.sh`,
`scripts/tests/test_agentdev_devcontainer_lifecycle.py`; Modify:
`.devcontainer/scripts/postCreateCommand.sh`,
`.devcontainer/scripts/postStartCommand.sh`,
`.devcontainer/scripts/postAttachCommand.sh`,
`.devcontainer/scripts/setup-agent-state.sh`

- [ ] Extract create-once project/client initialization, start readiness, and
  attach-scoped catalog/index refresh behind stable commands installed under
  `/opt/agentdev-runtime/`. Preserve restart and repeated-attach semantics and
  make each command idempotent.
- [x] Define ordered `/etc/agentdev/hooks/{created,started,attached}.d/`
  extension points. Run only executable files from those explicit directories,
  fail with the hook name and phase, and never discover or execute hooks merely
  because an untrusted workspace was mounted.
  - **Evidence:** commit 096c5c8f;
    `uv run pytest scripts/tests/test_agentdev_devcontainer_lifecycle.py` — 20
    passed, including order, skip, failure naming, and workspace-script refusal.
- [x] Retain the checkout-catalog override only when all required agentdev
  manifests are present. A normal consumer with no catalog must continue using
  the immutable staged catalog.
  - **Evidence:** commit 096c5c8f;
    `uv run pytest scripts/tests/test_agentdev_devcontainer_lifecycle.py` — 20
    passed, including complete and incomplete checkout catalogs.

### Task 4: Build the canonical image family

**Files:** Create: `docker/base/agentdev-base.Dockerfile`,
`docker/deploy/agentdev-deploy.Dockerfile`,
`docker/devcontainer/agentdev-devcontainer.Dockerfile`; Modify:
`docker/desktop/entrypoint.sh`, `docker/desktop/start-xpra.sh`, `.dockerignore`;
Delete: `docker/desktop/agent-desktop.Dockerfile`,
`docker/opencode/agent-opencode.Dockerfile`

- [ ] Rename the lifecycle-neutral `agent-desktop` build to `agentdev-base`
  without copying `.devcontainer/scripts/` into it. Preserve its tools, catalog,
  validators, default shell entrypoint, and multi-architecture build.
- [x] Rename `agent-opencode` to `agentdev-deploy`, derive it from the exact
  same-run `agentdev-base` digest, and keep its established deploy profile and
  public service contract.
  - **Evidence:** commit bcd8c5e2;
    `docker build -f docker/deploy/agentdev-deploy.Dockerfile` on the pinned
    base digest, then
    `AGENTDEV_RUNTIME_TEST_IMAGE=<that image> .devcontainer/scripts/test-agent-runtime.sh`
    — 24 passed, 1 skipped (no previous image).
- [x] Add `agentdev-devcontainer` as a sibling derived from the exact same-run
  base digest. Install the runtime scripts, both stable lifecycle commands and
  supervisor dependencies, declare the devcontainer profile entrypoint, and
  embed Dev Container metadata for lifecycle commands and default environment.
  - **Evidence:** commits bcd8c5e2, c4dcaeb3; with
    `AGENTDEV_DEVCONTAINER_TEST_IMAGE` set to a local build of commit bcd8c5e2,
    `uv run pytest scripts/tests/test_agentdev_devcontainer_image.py` — 5
    passed; the fixtures declare no managed commands, so the lifecycle came from
    the image metadata.

### Task 5: Consume the image in this repository

**Files:** Modify: `.devcontainer/devcontainer.json`,
`.devcontainer/docker-compose.yml`, `.devcontainer/devcontainer-init.sh`,
`devcontainer-compose-pins.yml`, `.devcontainer/devcontainer-lock.json`

- [ ] Point the canonical Dev Container at the pinned `agentdev-devcontainer`
  image, remove the Docker-in-Docker Feature and the `sleep infinity` command,
  and let the image entrypoint own supervised services. Retain SSH support, MCP
  sidecar wiring, workspace/worktree mounts, persistent state volumes, and the
  shared-auth volume.
- [x] Replace checkout-relative lifecycle commands with the image metadata or
  stable `/opt/agentdev-runtime/` commands. Keep `waitFor` tied to the runtime
  readiness command; editor startup must fail when the required service graph is
  not ready.
  - **Evidence:** commits 096c5c8f, bcd8c5e2, 480ea23f;
    `uv run pytest scripts/tests/test_agentdev_devcontainer_lifecycle.py` — 20
    passed, including the start phase failing on a failed or late runtime; with
    `AGENTDEV_DEVCONTAINER_TEST_IMAGE` set to a local build,
    `uv run pytest scripts/tests/test_agentdev_devcontainer_repository.py` — 3
    passed.
- [x] Prove this repository's checkout catalog wins after attachment and that a
  rebuild, restart, window reload, ordinary clone, and Git worktree preserve
  their intended state boundaries.
  - **Evidence:** commit 480ea23f; with `AGENTDEV_DEVCONTAINER_TEST_IMAGE` set
    to a local build of commit bcd8c5e2,
    `uv run pytest scripts/tests/test_agentdev_devcontainer_repository.py` — 3
    passed: clone and worktree through reload, restart, and rebuild, sharing
    only credentials.

### Task 6: Verify direct and derived consumers

**Files:** Create: `scripts/tests/fixtures/devcontainer-direct/`,
`scripts/tests/fixtures/devcontainer-derived/`,
`scripts/tests/test_agentdev_devcontainer_image.py`

- [ ] Build a fixture that references the published image contract without
  copying lifecycle scripts. Verify project dependency setup, pre-commit when
  configured, agent policy, CBM indexing, Xpra, nested Docker, and staged
  catalog availability.
- [ ] Build a derived fixture image that adds custom tooling and ordered hooks.
  Verify it retains managed startup, can override documented environment values,
  cannot require replacement of `/opt/agentdev-runtime`, and does not execute
  similarly named files from the mounted repository.
- [ ] Run both fixtures through create, stop/start, rebuild, and repeated attach
  events and assert the right phase runs exactly when specified.

### Task 7: Publish, pin, and accept all three canonical images

**Files:** Modify: `.github/workflows/ci.yml`,
`.github/actions/paths-filter/action.yml`,
`.github/actions/docker/promote/action.yml`, `.github/renovate.json`,
`.github/workflows/validate-renovate-config.yml`,
`.github/workflows/ai-responder.yml`, `devcontainer-compose-pins.yml`,
`opencode-compose-pins.yml`, `compose.opencode.yml`

- [ ] Build `agentdev-base` once per architecture and build `agentdev-deploy`
  and `agentdev-devcontainer` from that run's immutable base digest. Merge and
  promote moving tags only after deploy and Dev Container native acceptance
  succeeds.
- [ ] Rename deploy Compose, pins, Renovate rules, workflow outputs, and
  repository references to the canonical image names. Stop publishing the old
  `agent-desktop` and `agent-opencode` names rather than creating aliases.
- [ ] Run AI review and other development-image workflow jobs in the same pinned
  `agentdev-devcontainer` digest used by the repository Dev Container; keep
  digest-only pin changes outside the image build path filter.

### Task 8: Align the product contract and codebase map

**Files:** Create: `docs/knowledge/data/spec/agentdev-runtime-images.md`,
`docs/knowledge/data/architecture/devcontainer-runtime.md`; Modify: `README.md`,
`docs/user-stories/agent-containers.md`, `docs/knowledge/data/product.md`,
`docs/knowledge/data/spec/image-pinning.md`,
`docs/knowledge/data/spec/catalog-lifecycle.md`,
`docs/knowledge/data/spec/devcontainer-docker-storage.md`,
`docs/knowledge/data/architecture/nested-docker-provisioning.md`,
`docs/knowledge/data/architecture/template-boundary.md`,
`docs/knowledge/data/features/standalone-opencode-container.md`,
`docs/knowledge/data/codebase/`, `docs/knowledge/data/spec.md`,
`docs/knowledge/data/architecture.md`

- [ ] Document the canonical image family, profile boundary, lifecycle
  ownership, customization interface, and supported direct/derived/full adoption
  modes. State explicitly that `template-consume` remains supported for full
  adoption.
- [ ] Update image, catalog, Docker-storage, pinning, and product terminology to
  the shipped names and behaviour without copying runtime implementation detail
  into multiple documents.
- [ ] Refresh every stale codebase-map document through `/agentdev:iwe-map`
  after paths and flows settle.

### Task 9: Verify published multi-architecture images

**Files:** None.

- [ ] **Closed by: CI on the current head.** Both architectures publish the
  three candidate images, run deploy and Dev Container native acceptance, and
  promote the canonical moving tags only after every required check passes.

## Spec changes

### `data/spec/agentdev-runtime-images`

``` markdown
## ADDED Requirements

### Requirement: the base image is lifecycle-neutral

`agentdev-base` SHALL contain the shared development tools, agentdev catalog,
and default policy without containing deploy or Dev Container lifecycle
scripts.

#### Scenario: a consumer runs the base image directly

- **WHEN** a consumer starts `agentdev-base` with its own command
- **THEN** the tools and staged catalog are available, and no agentdev runtime
  supervisor or workspace lifecycle starts implicitly

### Requirement: deploy and Dev Container images are sibling runtimes

`agentdev-deploy` and `agentdev-devcontainer` SHALL derive from the same
accepted `agentdev-base` digest and SHALL package their own runtime entrypoint,
profile, and lifecycle surface.

#### Scenario: one base build feeds both runtimes

- **WHEN** CI builds an accepted image family
- **THEN** both runtime images identify the exact base digest produced in that
  run, without deriving either runtime image from the other

### Requirement: the Dev Container image owns persistent services

`agentdev-devcontainer` SHALL start Docker, D-Bus, keyring, CBM, and enabled
Xpra through its supervised entrypoint, SHALL publish readiness only after
required services are healthy, and SHALL recover or fail with the bounded
policy shared with deploy.

#### Scenario: an editor attaches to a healthy runtime

- **WHEN** the Dev Container start lifecycle waits for runtime readiness
- **THEN** attachment proceeds only after every required service reports ready

#### Scenario: a required service exhausts recovery

- **WHEN** a required service cannot recover within its configured budget
- **THEN** readiness is withdrawn, the failure names the service, and the
  container exits nonzero

### Requirement: lifecycle phases remain distinct

The image SHALL provide stable create, start/readiness, and attach commands and
SHALL NOT move create-once or attach-scoped work into the entrypoint.

#### Scenario: only the attach lifecycle runs

- **WHEN** an attach-only lifecycle event occurs
- **THEN** attach-scoped catalog and index refresh runs without rerunning
  create-once initialization or restarting supervised services

### Requirement: consumers do not copy lifecycle implementation

A direct or derived consumer SHALL be able to obtain the complete managed
lifecycle by referencing `agentdev-devcontainer` and SHALL customize it through
documented environment values and executable files in explicit ordered hook
directories.

#### Scenario: a direct consumer has no lifecycle scripts

- **WHEN** its descriptor selects the image, mounts, workspace, and editor
  settings without repository-local agentdev scripts
- **THEN** managed startup, lifecycle commands, tools, and the staged catalog
  remain available

#### Scenario: a derived image adds a hook

- **WHEN** it installs an executable hook in a documented phase directory
- **THEN** the hook runs in deterministic order after the managed phase without
  replacing files below `/opt/agentdev-runtime`

#### Scenario: a mounted repository contains a similarly named script

- **WHEN** no explicit image hook registers that script
- **THEN** mounting or attaching the repository does not execute it

### Requirement: the agentdev checkout overrides the staged catalog

The complete catalog in this repository's checkout SHALL override the staged
catalog on attach, while repositories without all required catalog manifests
SHALL continue using the staged version.

#### Scenario: an agentdev developer reloads the editor

- **WHEN** the checkout contains the Claude, Codex, and OpenCode catalog
manifests and the attach lifecycle runs
- **THEN** all three clients register the checkout catalog without rebuilding
the image

### Requirement: full adoption remains supported

`template-consume` SHALL remain a supported full-adoption workflow whose
adopted Dev Container uses the published runtime image; minimal adoption SHALL
not be a prerequisite for full adoption.

#### Scenario: an existing full-adoption repository updates

- **WHEN** it follows the supported template-consume update path
- **THEN** its repository-owned customization is preserved and its managed
runtime resolves through the published image contract
```

### [Image pinning](../spec/image-pinning.md)

``` markdown
## MODIFIED Requirements

### Requirement: images are pinned by tag and digest, never a bare moving tag

The canonical `agentdev-devcontainer` and `agentdev-deploy` consumer
configurations SHALL reference their image by tag and digest so an upstream
rebuild never silently changes a running environment.

#### Scenario: a canonical image is rebuilt with the same tag

- **WHEN** either canonical moving tag is rebuilt and pushed again
- **THEN** a consumer's pinned digest still resolves to the old image until the
  pinned digest is updated

### Requirement: workflow container images share the Dev Container pin

Every workflow job that runs in the development runtime SHALL reference the
same `agentdev-devcontainer` tag and digest as `devcontainer-compose-pins.yml`,
and a digest update SHALL move every reference in one change.

#### Scenario: Renovate bumps the Dev Container digest

- **WHEN** Renovate proposes a new `agentdev-devcontainer` digest
- **THEN** one pull request changes the Compose pin and every workflow
  `container.image` reference to that digest

#### Scenario: a bumped digest is exercised before merge

- **WHEN** a pull request changes the Dev Container digest
- **THEN** a required check runs inside it and the pull request cannot merge
  while that check fails

### Requirement: published tags name only tested images

CI SHALL publish `ubuntu-ansible`, `agentdev-base`, `agentdev-deploy`, and
`agentdev-devcontainer` candidates under immutable commit tags and SHALL move
event tags only after native deploy and Dev Container acceptance pass for the
same digests, without rebuilding. CI SHALL NOT move a tag to an image built
from an ancestor of the commit it names. Primary checks runs on `main` SHALL NOT
cancel one another.

#### Scenario: every acceptance check passes

- **WHEN** the run's image and runtime checks pass
- **THEN** the event's moving tags name the exact digests that run built and
  tested

#### Scenario: a check fails or the run is cancelled

- **WHEN** any required acceptance job fails or the run is cancelled
- **THEN** every moving tag keeps its previous digest, and only the immutable
  commit tag names the new image family

#### Scenario: an older run is re-run

- **WHEN** an older commit passes after a newer commit was promoted
- **THEN** moving tags keep the newer image family

#### Scenario: pushes to main arrive during a run

- **WHEN** commits land on `main` while its run is in progress
- **THEN** that run completes, and the newest waiting run follows it
```

### [Catalog lifecycle](../spec/catalog-lifecycle.md)

``` markdown
## MODIFIED Requirements

### Requirement: the catalog is installed in the base image and reconciled by the Dev Container create lifecycle

The agentdev catalog SHALL be installed in `agentdev-base` at image build time.
`agentdev-devcontainer` SHALL reconcile that catalog into mounted client-state
volumes during its create lifecycle after establishing persistent auth and
configuration links.

#### Scenario: a base-image consumer uses no lifecycle hooks

- **WHEN** it starts `agentdev-base` without client-state volumes
- **THEN** Claude, Codex, and OpenCode resolve the staged agentdev catalog

#### Scenario: a Dev Container starts with fresh client-state volumes

- **WHEN** the create lifecycle runs
- **THEN** it establishes persistent links before CBM configuration and installs
  the staged catalog into every mounted client state

#### Scenario: a Dev Container starts with an existing catalog install

- **WHEN** persistent client-state volumes shadow the build-time install
- **THEN** their unrelated state is preserved and the staged catalog is
  reconciled to the image version

### Requirement: this repository's checkout overrides the staged catalog on attach

The attach lifecycle SHALL register this checkout's complete Claude, Codex, and
OpenCode catalog over the staged copy and SHALL leave the staged copy selected
when the mounted repository does not contain a complete catalog.

#### Scenario: an agentdev developer reloads the editor

- **WHEN** this checkout's catalog changed and attach runs
- **THEN** all clients resolve the checkout version without an image rebuild

#### Scenario: a normal consumer attaches

- **WHEN** its repository has no complete agentdev catalog
- **THEN** attach succeeds without changing the staged catalog registration
```

### [Devcontainer Docker storage](../spec/devcontainer-docker-storage.md)

``` markdown
## MODIFIED Requirements

### Requirement: the Dev Container image supervises its nested Docker engine

`agentdev-devcontainer` SHALL run the nested Docker daemon through its managed
service profile on non-overlay persistent storage and SHALL apply the image's
BuildKit garbage-collection policy.

#### Scenario: Docker becomes ready

- **WHEN** the Dev Container runtime starts
- **THEN** runtime readiness remains blocked until the managed Docker daemon
  answers its probe

#### Scenario: Docker exhausts recovery

- **WHEN** the daemon cannot recover within its bounded budget
- **THEN** the runtime fails and reports Docker as the terminal service

### Requirement: the Dev Container engine limits its build cache

The image's Docker configuration SHALL enable BuildKit garbage collection with
a 10 GB build-cache limit, and the supervised daemon SHALL run with it.

#### Scenario: the build cache passes the limit

- **WHEN** builds inside the Dev Container push the build cache past 10 GB
- **THEN** BuildKit garbage collection reduces it to at most 10 GB
```

## Depends on

[Ship a standalone OpenCode
container](20261017-standalone-opencode-container.md)

## Verification

- `uv run pytest scripts/tests/test_agent_runtime_profiles.py`
- `uv run pytest scripts/tests/test_agentdev_devcontainer_lifecycle.py`
- `uv run pytest scripts/tests/test_agentdev_devcontainer_image.py`
- `uv run pytest scripts/tests/test_agent_runtime_supervision.py`
- `uv run pytest scripts/tests/test_agent_runtime_identity.py`
- `uv run pytest scripts/tests/test_agent_runtime_workspace.py`
- `uv run pytest scripts/tests/test_agent_runtime_docker.py`
- `uv run pytest scripts/tests/test_agent_runtime_keyring.py`
- `uv run pytest scripts/tests/test_agent_runtime_cbm.py`
- `.agents/plugins/agentdev/bin/python-lint-check.sh`
- Run `shellcheck` on every created or modified shell script.
- Build the three-image family locally through the repository's image-build
  action or the microVM sandbox, then inspect each image's labels, ancestry,
  entrypoint, healthcheck, catalog, and runtime files.
- Run the direct and derived fixtures through Dev Container create, stop/start,
  rebuild, and repeated attach operations; confirm their per-phase counters and
  required service health.
- Run `iwe normalize`, `iwe schema validate`, and the knowledge-base tests.
- Run `/agentdev:iwe-map` refresh and confirm no changed mapped source remains
  stale.
- Confirm CI on the current head builds and accepts amd64 and arm64 candidates
  before promoting the canonical tags.

## Out of scope

- The first-class external-workspace launcher for repositories with no local Dev
  Container descriptor.
- Extracting the reusable IWE-bootstrap skill or changing `iwe-setup` and
  `iwe-map` onboarding.
- Removing or deprecating `template-consume`; full adoption remains supported.
- Installing repository-specific knowledge, build, or review CI workflows.
- Running more than one target repository inside one Dev Container instance.
- Providing compatibility aliases for `agent-desktop` or `agent-opencode`.
- Starting Claude or Codex interfaces automatically.

## Key references

Verified anchor points (line numbers as of 2026-10-23):

- `.github/workflows/ci.yml:26` — image-name environment and image-family build
  pipeline
- `docker/desktop/agent-desktop.Dockerfile:5` — current lifecycle-neutral image
  base
- `docker/opencode/agent-opencode.Dockerfile:22` — runtime-script packaging
  boundary
- `docker/opencode/agent-opencode.Dockerfile:65` — current supervised entrypoint
- `docker/opencode/supervisord.conf:36` — current deploy service definitions
- `.devcontainer/scripts/runtime-supervisor.py:46` — runtime settings and
  service graph
- `.devcontainer/scripts/runtime-supervisor.py:352` — PID 1 bootstrap and
  supervisor entrypoint
- `.devcontainer/devcontainer.json:19` — current workspace and Feature
  configuration
- `.devcontainer/devcontainer.json:262` — checkout-relative lifecycle commands
- `.devcontainer/docker-compose.yml:57` — current development image selection
- `.devcontainer/docker-compose.yml:105` — current keepalive command replacing
  image command
- `.devcontainer/scripts/postCreateCommand.sh:53` — create-scoped agent state
  and catalog setup
- `.devcontainer/scripts/postStartCommand.sh:9` — start-scoped persistent
  services
- `.devcontainer/scripts/postAttachCommand.sh:8` — attach-scoped index and
  catalog refresh
