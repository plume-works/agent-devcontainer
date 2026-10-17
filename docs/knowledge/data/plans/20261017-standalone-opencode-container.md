---
type: plan
created: 2026-10-17
release:
- features/standalone-opencode-container
description: Publish agent-opencode with shared lifecycle helpers, configurable non-root identity, supervised project services, persistent state, and external-proxy Compose deployment.
generated:
  by: opencode/openai-gpt-6.1-sol
  at: 2026-10-17T05:34:21Z
sources:
- resource: docker/desktop/agent-desktop.Dockerfile
- resource: .dockerignore
- resource: .devcontainer/devcontainer.json
- resource: .devcontainer/scripts/postCreateCommand.sh
- resource: .devcontainer/scripts/postStartCommand.sh
- resource: .devcontainer/scripts/setup-keyring.sh
- resource: .devcontainer/scripts/link-codex-auth.sh
- resource: .devcontainer/scripts/link-opencode-auth.sh
- resource: .devcontainer/scripts/opencode-web-start.sh
- resource: .github/workflows/ci.yml
- resource: .github/renovate.json
- resource: https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/v0.12.1/src/main.c
- resource: https://github.com/sst/opencode/blob/v1.19.3/packages/opencode/src/cli/cmd/serve.ts
- resource: https://github.com/sst/opencode/blob/v1.19.3/packages/opencode/src/cli/cmd/web.ts
---

# Ship a standalone OpenCode container

## Context

[Standalone OpenCode container](../features/standalone-opencode-container.md)
defines a single-project environment operated without Coder or a Dev Containers
client. The image must own startup and persistent-state reconciliation rather
than require its project to contain lifecycle scaffolding.

[OpenCode web](../spec/opencode-web.md) supplies the Coder server and
auth/session contract. [Agent auth
persistence](../architecture/agent-auth-persistence.md) separates shared
provider logins from instance state. This work extends those building blocks
with a dedicated image, not a new default for `agent-desktop`.

[Nested Docker provisioning](../architecture/nested-docker-provisioning.md)
assigns DinD to the Dev Containers feature. The standalone image needs its own
supervised daemon; the existing devcontainer remains feature-managed. [Image
pinning](../spec/image-pinning.md) applies to the new consumer examples and
publishing flow as well.

## Approach

Derive `ghcr.io/plume-works/agent-opencode` from the same-run digest of
`agent-desktop`. Bake the canonical helpers from `.devcontainer/scripts/` into
`/opt/agentdev-runtime`; use explicit home, workspace, auth, and runtime paths
so those helpers also remain callable by the existing lifecycle hooks. Reject
copying the entire checkout into the image or invoking the root-specific hooks
unchanged. Keep `/opt/agentdev` immutable and separate from writable user state.

Use an explicitly installed foreground `supervisord` as PID 1, with a root
bootstrap for account/volume setup and root DinD, and user-owned agent services.
An event listener owns dependency transitions, bounded restart budgets,
readiness, and terminal failure. Do not rely on `startretries` alone to bound
crashes after a service reaches RUNNING. OpenCode runs foreground; retain the
existing Coder tmux launcher as an adapter over shared network/link
construction. Standalone uses `opencode serve`, which invokes the same server
without opening a browser, and retains DISPLAY for graphical tools spawned by
OpenCode. Verify its web assets against the shipped version in container
acceptance.

The runtime user is `agent`, home `/home/agent`, numeric IDs from
`AGENTDEV_UID`/`AGENTDEV_GID` (both default `1000`), with passwordless sudo.
System tools live outside `/root`; user configuration is reconciled into the
runtime home after mounts. Use a per-project home volume, `/uv` volume,
workspace volume or bind, and `/var/lib/docker` volume. Share only agent
credentials at `/var/lib/agentdev/auth`, selected through
`AGENTDEV_AGENTS_AUTH_DIR`. Require equal UID/GID within each sharing cohort;
initialize an empty shared volume under a lock, reject a populated incompatible
one, and never recursively chown the workspace, its ancestors, or another
container's credential store.

GitHub authentication uses injected `GH_TOKEN`/`GITHUB_TOKEN`. No shared gh
configuration, interactive-login persistence facility, credential broker, or
shared keyring database is added. D-Bus and keyring remain instance-local.

Startup order is identity/mount validation, optional firewall, user
D-Bus/keyring and root DinD readiness, workspace validation/clone, auth and
client/catalog configuration, matching project setup, CBM daemon and initial
index, Xpra readiness, then OpenCode. Configure GitHub HTTPS credential handling
before a private clone. Network-facing services are reachable only through an
existing external proxy network; Compose publishes no host ports.

Implementation defaults: three recovery attempts per required service with
1/2/4-second backoff, reset only after 60 seconds continuously healthy;
60-second service-start deadlines, a configurable preparation deadline
defaulting to 1800 seconds, and a 30-second graceful-stop deadline before forced
cleanup. Tests may shorten these values. Expose configuration through documented
`AGENTDEV_*` variables, not command strings evaluated by a shell.

## Implementation Steps

### Task 1: Establish the non-root CBM lifecycle contract

**Files:** Create: `scripts/tests/test_agent_runtime_cbm.py`,
`.devcontainer/scripts/runtime-cbm.sh`

- [ ] Write focused tests against the shipped CBM pin for non-root cache/home
  ownership, a mounted Git checkout, authenticated daemon status, death
  detection, restart, and graceful shutdown. Keep test repositories and caches
  below the repo-root `.tmp/`; use an isolated user/cache/endpoint so the tests
  cannot stop the developer's daemon.
- [ ] Implement an adapter using the supported `daemon start/status/stop`
  interface. Track actual daemon identity and readiness, not just the
  short-lived starter process; detect generation changes and never kill a reused
  PID. Account for MCP clients auto-starting a replacement daemon. On shutdown
  close managed clients first, then stop CBM and bound any remaining process
  cleanup.
- [ ] Verify the native client-config installation under the runtime user
  preserves the image's exact CBM version/build, user-owned installation path,
  and canonical cache root without fetching an unpinned replacement. If the pin
  cannot satisfy lifecycle, installation, or ownership requirements, stop and
  revise this plan before depending on an unsupported internal daemon command,
  changing ownership of the mounted checkout, or upgrading CBM.

### Task 2: Make shared auth and configuration helpers identity-aware

**Files:** Create: `.devcontainer/scripts/runtime-paths.sh`,
`.devcontainer/scripts/setup-agent-state.sh`,
`scripts/tests/test_agent_runtime_state.py`; Modify:
`.devcontainer/scripts/link-codex-auth.sh`,
`.devcontainer/scripts/link-opencode-auth.sh`,
`.devcontainer/scripts/postCreateCommand.sh`,
`.devcontainer/scripts/postStartCommand.sh`,
`.devcontainer/scripts/codebase-memory-mcp-install.sh`,
`.devcontainer/scripts/setup-gh-credential-helper.sh`

- [ ] Test explicit runtime HOME/CODEX_HOME/XDG/auth roots alongside unchanged
  root devcontainer defaults, fresh/existing volumes, regular-file credential
  migration, symlink repair, and preservation of unrelated user configuration.
- [ ] Extract agent-state initialization, including `.claude.json` linking
  before CBM config installation, auth directories, Codex policy, and catalog
  registration. Let both hooks and standalone preparation call the same
  primitives; keep devcontainer scope, call order, opt-outs, and nonfatal/fatal
  behavior compatible. Standalone required operations fail explicitly.
- [ ] Parameterize GitHub helper setup's runtime environment-file location,
  preserve an existing matching helper, and configure injected-token HTTPS
  access for clone and later Git operations without persisting tokens or
  exposing them in logs. Include private-clone ordering in the tests.

### Task 3: Share keyring setup with supervised service execution

**Files:** Create: `.devcontainer/scripts/runtime-keyring.sh`,
`scripts/tests/test_agent_runtime_keyring.py`; Modify:
`.devcontainer/scripts/setup-keyring.sh`,
`.devcontainer/scripts/setup-gh-credential-helper.sh`

- [ ] Separate reusable keyring initialization/readiness/environment logic from
  lifecycle background launching. Preserve existing saved secrets and the
  existing headless keyring storage policy; never share its database between
  instances or persist session PIDs/sockets as durable state.
- [ ] Provide foreground D-Bus/keyring execution with a deterministic private
  runtime socket and explicit `XDG_RUNTIME_DIR`; make the same environment
  available to OpenCode, Xpra, CLI tools, and documented `docker exec` usage.
  Verify Secret Service access from an OpenCode-style child process, recovery
  after keyring/D-Bus replacement, and old devcontainer background behavior.

### Task 4: Implement runtime identity and volume validation

**Files:** Create: `.devcontainer/scripts/runtime-bootstrap.sh`,
`scripts/tests/test_agent_runtime_identity.py`

- [ ] Test default and custom numeric IDs, invalid IDs, existing account/group
  collisions, passwordless sudo, writable instance mounts, shared-auth ownership
  mismatch, and concurrent initialization of an empty auth volume.
- [ ] Create or safely reuse the runtime account and supplementary Docker group;
  set home/runtime directories and narrowly scoped passwordless sudo. Initialize
  ownership only on managed instance storage and an empty locked credential
  volume. Reject incompatible populated state instead of recursively rewriting
  ownership. Never alter bind-checkout ownership or its ancestors.
- [ ] Keep PID/socket/runtime state ephemeral, secrets out of startup output,
  and clear errors for missing/wrong mounts, unwritable checkout, and
  incompatible UID/GID. A container restart does not rerun account migration on
  another instance's shared state.

### Task 5: Prepare exactly one workspace without destructive updates

**Files:** Create: `.devcontainer/scripts/runtime-workspace.sh`,
`scripts/tests/test_agent_runtime_workspace.py`; Modify:
`.devcontainer/scripts/uv-sync.sh`, `.devcontainer/scripts/setup-pre-commit.sh`,
`.devcontainer/scripts/setup-git-safe-directory.sh`,
`.devcontainer/scripts/postAttachCommand.sh`,
`.devcontainer/scripts/reinstall-agentdev-claude.sh`,
`.devcontainer/scripts/reinstall-agentdev-codex.sh`,
`.devcontainer/scripts/reinstall-agentdev-opencode.sh`

- [ ] Support `DEV_WORKSPACE_FOLDER` default `/workspaces/project`,
  `AGENTDEV_REPOSITORY_URL` for first clone, and optional
  `AGENTDEV_REPOSITORY_REF` for an initial branch/tag. A valid existing checkout
  wins without network Git operations; an empty destination without a URL or a
  nonempty invalid destination fails. Validate external Git common-directory
  access for bind-mounted worktrees and document necessary extra mounts.
- [ ] Test dirty checkout preservation, interrupted-clone retry refusal without
  deletion, missing worktree metadata, GitHub token authentication, and clone
  errors without credentials in logs. Do not run `.venv` migration, Git reset,
  clean, fetch, pull, or branch switching against a reused workspace.
- [ ] Reuse uv synchronization only for `pyproject.toml` projects, with the
  existing all-groups/all-extras semantics and explicit `/uv` environment; run
  pre-commit setup only when its configuration exists. In strict standalone mode
  failures propagate instead of merely logging success. Respect an existing
  configured Git hook path and do not replace custom hooks silently; report
  conflicts. Test both present/absent configuration and failure paths.
- [ ] Select a valid checkout agentdev catalog when its manifests/bridge exist,
  otherwise the image catalog. Reconcile all three clients at each container
  start, preserving unrelated config and removing stale managed registrations.
  Run configuration before CBM is started and OpenCode reads its plugins.
  Preserve default helper behavior for existing devcontainer callers.

### Task 6: Supervise services and enforce readiness/recovery

**Files:** Create: `.devcontainer/scripts/runtime-supervisor.py`,
`.devcontainer/scripts/runtime-health.sh`, `docker/opencode/supervisord.conf`,
`scripts/tests/test_agent_runtime_supervision.py`

- [ ] Test startup ordering, bounded deadlines, preparation failure blocking
  OpenCode, per-service recovery, dependency outages, readiness loss, and retry
  exhaustion after RUNNING as well as startup failures. Failed readiness counts
  against the same recovery budget; do not treat an endlessly hung process as
  healthy. Terminal failure must make PID 1 exit nonzero, not just stop
  children.
- [ ] Manage root DinD and user D-Bus/keyring, CBM adapter, Xpra, and OpenCode;
  use controlled foreground processes or identity-aware adapters. Pipe service
  output to stdout/stderr. Track preparation as a one-shot gate; do not rerun
  uv/catalog mutation on an ordinary individual service restart.
- [ ] Pause dependent readiness during recovery, refresh connection state for
  affected clients, and recover coherently after D-Bus or CBM changes without
  duplicating daemons. Publish aggregate readiness only after required probes
  pass. Handle SIGTERM with ordered shutdown: agent/client processes before CBM,
  desktop and keyring, then DinD; bound and reap entire managed process groups.

### Task 7: Run and persist the dedicated nested Docker engine

**Files:** Create: `.devcontainer/scripts/runtime-docker.sh`,
`scripts/tests/test_agent_runtime_docker.py`; Reuse:
`.devcontainer/scripts/docker-image-prune.sh`,
`ansible/roles/install_docker/tasks/main.yml`

- [ ] Start exactly one root `dockerd` using `/etc/docker/daemon.json`, private
  Unix socket and per-instance `/var/lib/docker` storage; make it accessible to
  the runtime user without mounting the host socket or exposing a TCP listener.
  Validate privileged mode, storage backing, readiness, and replacement after a
  daemon crash. Persist all Docker data used by the shipped engine, including
  any enabled containerd image store, rather than assuming one volume suffices.
- [ ] Run the shared unused-image prune once the engine is ready and retain its
  nonfatal behavior and 72-hour policy; retain 10 GB BuildKit GC. Exercise
  nested `hello-world`, an actual build, engine restart, and persistent image
  reuse in the container acceptance harness. Do not also invoke a Dev Containers
  feature daemon initializer.

### Task 8: Adapt OpenCode and Xpra for foreground proxy access

**Files:** Create: `.devcontainer/scripts/opencode-web-command.sh`,
`scripts/tests/test_agent_runtime_ingress.py`; Modify:
`.devcontainer/scripts/opencode-web-start.sh`, `docker/desktop/start-xpra.sh`,
`scripts/tests/test_opencode_web_start.py`

- [ ] Extract command/link construction without changing the Coder tmux contract
  or its tests. Standalone runs OpenCode foreground in the workspace on
  `0.0.0.0:4096`, using `opencode serve` with mandatory nonempty
  `OPENCODE_SERVER_PASSWORD`. Preserve DISPLAY for agent child processes and
  test graphical tool access without opening a browser at server startup. Keep
  Coder's `opencode web` command and DISPLAY removal unchanged.
- [ ] Run Xpra foreground on container port 14500, with no Xpra password and
  external proxy authentication as the access boundary. Retain
  `AGENTDEV_SKIP_XPRA`; when enabled, Xpra is required for readiness and
  recovery. Add strict supervised execution without weakening existing lifecycle
  behavior.
- [ ] Use authenticated OpenCode API readiness in addition to web-asset checks;
  test HTTP/WebSocket routing at the server root, password rejection, and the
  absence of host-published ports. Do not bake a Coder-specific URL, password,
  or proxy configuration into the image.

### Task 9: Preserve the opt-in firewall in standalone networking

**Files:** Create: `.devcontainer/scripts/runtime-firewall.sh`,
`scripts/tests/test_agent_runtime_firewall.py`; Reuse:
`.devcontainer/scripts/firewall.sh`,
`ansible/roles/devcontainer_firewall/files/init-firewall.sh`,
`.devcontainer/firewall-allowlist.txt`

- [ ] Leave the firewall inert unless `ENABLE_FIREWALL=true`. In enabled mode,
  use an explicit allowlist or a baked default without requiring project
  scaffolding; fail on invalid configuration. Apply base rules before DinD so
  subsequent daemon network setup is not erased by a rule flush.
- [ ] Allow only configured trusted proxy source CIDRs to the required web ports
  when the firewall is enabled; retain existing egress/IPv6 policy and
  self-checks. Test proxy access, forbidden egress, GitHub access, and nested
  Docker networking together. Keep the old devcontainer firewall contract
  intact.

### Task 10: Build the dedicated image with non-root-accessible tools

**Files:** Create: `docker/opencode/agent-opencode.Dockerfile`; Modify:
`.dockerignore`; Reuse: `docker/desktop/agent-desktop.Dockerfile`,
`ansible/roles/agentic_tools/tasks/install_catalog.yml`,
`ansible/roles/github_cli/tasks/main.yml`

- [ ] Derive from an explicit supplied `agent-desktop` digest. Install
  supervisor and its required utilities explicitly. Bake helpers/config/default
  allowlist, narrowly reopening `.devcontainer/scripts` and the allowlist in
  `.dockerignore` without including `.env`, generated metadata, auth, or
  workspace contents.
- [ ] Audit the inherited tool inventory as the runtime user, relocating any
  root-home executables/support files to root-owned system paths and registering
  user-scoped tooling in the runtime home. Include `gh stack`, validator,
  uv/bun/node, agents, CBM, IWE, shell/lint/build tools, desktop, and Docker. Do
  not make `/root` traversable or put user-writable directories ahead of managed
  tools to hide missing installation work.
- [ ] Set dedicated entrypoint/CMD, user/home/path defaults, container ports,
  healthcheck, and image labels. Keep `agent-desktop` ENTRYPOINT/CMD and the
  Coder agent start compatible. Fresh user state is initialized after mounts,
  not by relying on a copied root home or first-use volume copy-up.

### Task 11: Supply supported Compose deployment configurations

**Files:** Create: `compose.opencode.yml`, `compose.opencode.bind.yml`,
`opencode-compose-pins.yml`, `docker/opencode/runtime.env.example`,
`scripts/tests/test_agent_runtime_compose.py`

- [ ] Provide a clone-volume base and a bind-checkout override using the same
  fixed in-container workspace path. Compose creates project-scoped home, uv,
  workspace, Docker and any additional required Docker-store volumes, plus a
  named shared agent-auth volume whose name can be overridden per identity
  cohort. Verify the bind override replaces rather than duplicates the target
  workspace mount.
- [ ] Require an existing operator-named proxy network and supplied OpenCode
  password; publish no host ports, and include no MCP sidecar, Docker Desktop
  socket/secret mounts, or host Docker socket. Document privileged DinD, volume
  identity requirements, proxy routes to 4096/14500, Xpra authentication at the
  proxy, GitHub token injection, service opt-outs, and Git identity forwarding
  without empty `GIT_*` overrides.
- [ ] Put the real tag-and-digest pin in root-level `opencode-compose-pins.yml`,
  outside image-build inputs, and require that override in every supported
  launch command. The final pin comes from a published image; never invent a
  digest. Validate Compose rendering for clone, bind, custom IDs, and disabled
  Xpra without printing secret values.

### Task 12: Add repeatable container acceptance tests

**Files:** Create: `.devcontainer/scripts/test-agent-runtime.sh`,
`scripts/tests/test_agent_runtime_acceptance.py`

- [ ] Build a bounded acceptance harness against `AGENTDEV_RUNTIME_TEST_IMAGE`
  using isolated Compose project names, volumes, proxy fixture, temporary
  repositories and cleanup traps. Keep artifacts under repo-root `.tmp/` and do
  not spend provider/model usage for ordinary acceptance tests.
- [ ] Cover fresh bind and clone starts; non-Python and uv/pre-commit projects;
  custom IDs and sudo; real CBM query; Secret Service child access; nested
  Docker build; authenticated OpenCode API/assets; Xpra HTTP/WebSocket; and
  preparation failure keeping OpenCode unavailable.
- [ ] Cover restart, replacement, an actual older/newer image upgrade with
  persistent user config, shared provider-auth files with isolated sessions, two
  concurrent containers, UID mismatch rejection, unavailable worktree metadata,
  dirty-tree preservation, required-service crash/hang and exhausted recovery,
  and bounded clean stop. Distinguish file-persistence tests from the live
  provider-login check in Task 16.

### Task 13: Integrate native builds, manifests, pins, and CI gates

**Files:** Modify: `.github/workflows/ci.yml`,
`.github/actions/paths-filter/action.yml`, `.github/renovate.json`; Create:
`.github/workflows/opencode-runtime-checks.yml`,
`scripts/tests/test_agent_runtime_ci.py`; Reuse:
`.github/actions/docker/build-push-action/action.yml`,
`.github/actions/docker/multiarch-merge/action.yml`,
`.github/actions/docker/metadata-action/action.yml`

- [ ] Build `agent-opencode` after each native desktop build using that build's
  exact digest; publish per-arch artifacts and a distinct multi-arch manifest
  using existing tag conventions. Include amd64 and arm64 acceptance jobs,
  enforce their result in the CI completion gate, and retain existing desktop
  smoke/regression jobs.
- [ ] Register the root Compose pin with Renovate and post-upgrade file filters.
  A pin-only update runs acceptance against the proposed digest without
  rebuilding the image or creating a self-triggering publish/pin loop. Test
  path-filter and workflow behavior for runtime source changes versus pin-only
  changes.

### Task 14: Document the runtime and refresh its codebase map

**Files:** Modify: `README.md`, `docs/knowledge/data/product.md`; Create:
`docs/knowledge/data/architecture/standalone-opencode-runtime.md`; Refresh:
`docs/knowledge/data/codebase/docker.md`,
`docs/knowledge/data/codebase/api-image-runtime.md`,
`docs/knowledge/data/codebase/devcontainer/scripts.md`,
`docs/knowledge/data/codebase/flow-image-build.md`, and other stale mapped
sources

- [ ] Document supported bind/clone launch commands, external proxy and password
  setup, first provider login, injected GitHub tokens, stable paths, UID
  cohorts, storage lifecycle/backup, service status/logs, upgrade and failure
  recovery. Record the supervised standalone DinD design as a new scoped
  architecture document referencing the existing feature-managed devcontainer
  decision; include rejected whole-hook reuse, shared-home/auth, and tmux
  lifetime options.
- [ ] Update product distribution/runtime context and refresh maps through
  `/agentdev:iwe-map`; record only settled interfaces, not investigation
  history. Durable specs are merged from the deltas below during Ship.

### Task 15: Verify published native images and usable deployment pins

**Files:** Modify: `opencode-compose-pins.yml` with the verified published
digest

- [ ] **Closed by: CI and the implementing session after publication.** On the
  final candidate, read the passing amd64/arm64 acceptance results, inspect the
  published manifest and its same-run desktop ancestry, insert its real digest
  into the deployment pin, and pass pin-only acceptance. This external gate is
  separate from writing publishing code and cannot close on a local build.

### Task 16: Verify actual login/session continuity behind the operator proxy

**Files:** none; operator deployment of the published candidate

- [ ] **Closed by: maintainer with the external proxy and provider login.**
  Launch the documented deployment, connect a provider and create a session,
  replace the container and upgrade to a newer tested image with the same
  volumes; verify login, session, and user config continuity. Run a second
  same-ID project container and verify shared login with isolated sessions,
  healthy proxy access to OpenCode/Xpra, and proxy protection of the desktop.
  Keep credentials out of evidence. Do not substitute synthetic auth JSON for
  this gate.

## Spec changes

Create `spec/standalone-opencode-runtime` with the following full contract.
[OpenCode web](../spec/opencode-web.md), [Devcontainer Git
credentials](../spec/devcontainer-git-credentials.md), and [Devcontainer Docker
storage](../spec/devcontainer-docker-storage.md) keep their existing
integration-specific requirements; shared-helper extraction preserves them. The
standalone requirements below define strict startup and injected-token behavior
without changing Coder's tmux/failure semantics.

``` markdown
## ADDED Requirements

### Requirement: a dedicated image owns a single-project runtime

`ghcr.io/plume-works/agent-opencode` SHALL derive from the corresponding digest
of `agent-desktop`, provide linux/amd64 and linux/arm64 images, and start its
environment without Coder, a Dev Containers client, or project scaffolding.
It SHALL keep Claude Code and Codex available without autostarting them and
SHALL omit Docker MCP gateway integration.

#### Scenario: an ordinary checkout is mounted

- **WHEN** an operator starts the dedicated image with valid required configuration
- **THEN** it prepares that single project and starts OpenCode and its required services using image-owned shared helpers.

#### Scenario: the existing image is used

- **WHEN** an existing consumer starts agent-desktop or runs its devcontainer hooks
- **THEN** its command defaults, Coder integration, opt-outs, and lifecycle failure semantics remain compatible.

### Requirement: runtime identity preserves workspace and credential ownership

Agent tools SHALL run with configured numeric UID/GID, default 1000:1000, and
passwordless sudo. DinD and privileged initialization SHALL have the permissions
they require. Containers sharing an agent-auth volume SHALL use the same numeric
UID/GID. Initialization SHALL NOT recursively change workspace/ancestor or
populated shared-auth ownership and SHALL reject incompatible state explicitly.

#### Scenario: a custom identity starts

- **WHEN** writable instance volumes and shared-auth ownership match the configured IDs
- **THEN** agent tools, caches, client configuration, and sudo work as that user without access to root's private home.

#### Scenario: shared ownership is incompatible

- **WHEN** an existing auth volume belongs to another identity
- **THEN** startup fails without changing its ownership or credential content.

### Requirement: startup prepares or reuses one workspace

The runtime SHALL support a bind-mounted checkout or first clone into an empty
persistent workspace, defaulting to /workspaces/project. It SHALL preserve an
existing checkout without fetch, pull, reset, clean, branch switching, or
ownership migration. It SHALL authenticate supported GitHub HTTPS operations
with injected GH_TOKEN/GITHUB_TOKEN without storing those tokens. It SHALL run
matching uv and pre-commit preparation and complete initial CBM indexing before
OpenCode becomes available; errors and timeouts SHALL fail startup.

#### Scenario: the first clone is private

- **WHEN** an empty destination, repository URL, and valid injected token are supplied
- **THEN** startup configures noninteractive HTTPS authentication before cloning and prepares the checkout without logging the token.

#### Scenario: a dirty checkout restarts

- **WHEN** the workspace has local edits and a selected branch
- **THEN** startup preserves the branch and edits, performs only the supported project preparation, and does not automatically contact Git remotes.

#### Scenario: preparation cannot complete

- **WHEN** required worktree metadata is absent, a nonempty destination is invalid, a custom hook conflicts, setup fails, or indexing times out
- **THEN** startup reports the cause and OpenCode remains unavailable.

### Requirement: state survives replacement without cross-project session sharing

The runtime SHALL persist workspace, instance home/configuration, keyrings,
caches/environments, and nested Docker storage. Only Claude/Codex/OpenCode
provider credentials SHALL be shared across project containers. Startup SHALL
repair their auth links and reconcile managed client/catalog configuration
after mounts on every container start while preserving unrelated settings and
session data. It SHALL NOT add shared interactive GitHub-login storage.

#### Scenario: an image is upgraded with existing volumes

- **WHEN** a newer image starts against compatible persisted state
- **THEN** required managed configuration is current and provider logins, sessions, and unrelated user configuration remain usable.

#### Scenario: two project containers run

- **WHEN** same-ID containers mount the same agent-auth volume and different instance volumes
- **THEN** they see shared provider credentials but have independent sessions, keyring databases, caches, and Docker engines.

### Requirement: required services have supervised bounded recovery

The runtime SHALL supervise OpenCode, DinD, CBM, D-Bus/keyring, and enabled Xpra
with readiness probes, bounded startup, bounded per-service retries/backoff,
and orderly termination. It SHALL detect actual daemon failure even when the
public tool daemonizes. It SHALL mark dependency outages unready, recover
affected clients coherently, and exit nonzero after recovery exhaustion.
Xpra SHALL start by default with an explicit disable option.

#### Scenario: a running service fails

- **WHEN** a required process exits or fails readiness
- **THEN** the runtime becomes unready and restarts that service within its recovery budget without duplicating daemons or rerunning project mutation unnecessarily.

#### Scenario: failures continue

- **WHEN** a service exhausts its bounded recovery budget
- **THEN** remaining managed processes stop and the container exits nonzero.

#### Scenario: the container is stopped

- **WHEN** PID 1 receives SIGTERM
- **THEN** it stops managed clients and services in dependency order, bounds shutdown, and reaps remaining processes.

### Requirement: browser access uses an external proxy

Supported Compose deployments SHALL publish no host ports and SHALL connect to
an operator-provided proxy network. OpenCode SHALL require a nonempty server
password and bind container port 4096 on a network-reachable interface. Enabled
Xpra SHALL serve port 14500 without its own password; deployment instructions
SHALL require proxy authentication for it. Authenticated API readiness SHALL
not be inferred solely from a public static asset response.

#### Scenario: a password is missing

- **WHEN** the standalone runtime has no nonempty OpenCode server password
- **THEN** configuration validation fails instead of exposing an unauthenticated service or a silently unreachable loopback listener.

#### Scenario: proxy requests reach the runtime

- **WHEN** an authorized user accesses the configured proxy routes
- **THEN** OpenCode API/assets and Xpra HTTP/WebSocket work, and OpenCode rejects API requests lacking its password.

### Requirement: nested Docker and opt-in firewall retain their policies

The runtime SHALL operate its own persisted DinD engine through a private Unix
socket, without a host socket mount or Docker TCP listener. It SHALL retain
10 GB BuildKit GC and startup pruning of unused images older than 72 hours,
with prune errors nonfatal. The egress firewall SHALL remain opt-in; enabled
configuration SHALL retain its allowlist/IPv6 policy and self-checks while
supporting explicitly trusted proxy ingress and nested Docker operation.

#### Scenario: the engine restarts

- **WHEN** the container or nested daemon is replaced using its persistent storage
- **THEN** its existing images remain available and builds run as the runtime user.

#### Scenario: the firewall is enabled

- **WHEN** a valid allowlist and trusted proxy sources are configured
- **THEN** required proxy access and nested builds work, forbidden egress remains blocked, and daemon network rules are not erased by startup ordering.
```

Add to [Catalog lifecycle](../spec/catalog-lifecycle.md), preserving all current
requirements and scenarios:

``` markdown
## ADDED Requirements

### Requirement: standalone startup selects and reconciles the runtime catalog

Standalone agent-opencode startup SHALL use a valid checkout-provided agentdev
catalog when present and otherwise the immutable image catalog. It SHALL
reconcile Claude, Codex, and OpenCode configuration as the runtime user after
mounts and before OpenCode starts, including generated Codex agents, without
removing unrelated user settings or agents.

#### Scenario: the project provides the catalog

- **WHEN** the checkout contains the required catalog manifests and bridge
- **THEN** all three clients use that checkout catalog for the container start.

#### Scenario: a catalog is absent or the image is upgraded

- **WHEN** a checkout has no catalog or a newer bundled catalog is selected
- **THEN** startup applies the selected bundled catalog over stale managed registrations and preserves unrelated configuration.
```

Add to [Image pinning](../spec/image-pinning.md), preserving all current
requirements and scenarios:

``` markdown
## ADDED Requirements

### Requirement: standalone runtime deployment is digest-pinned and tested

Supported agent-opencode Compose launch commands SHALL include a tag-and-digest
pin in root-level opencode-compose-pins.yml. Runtime builds SHALL use the exact
agent-desktop digest from their build run. Pin-only changes SHALL exercise the
proposed runtime image on supported architectures without rebuilding/publishing
the image they consume.

#### Scenario: runtime sources change

- **WHEN** a runtime image is built and published
- **THEN** native amd64 and arm64 builds and acceptance checks gate success and the manifest identifies the corresponding desktop ancestry.

#### Scenario: only a deployment digest changes

- **WHEN** Renovate advances opencode-compose-pins.yml
- **THEN** acceptance runs against that digest, the image-build path filter does not match, and the update does not create a publish/pin loop.
```

## Depends on

[Autostart the OpenCode web UI on
Coder](20261016-opencode-web-coder-autostart.md) must land first.

## Verification

- Run focused pytest files from each task before its checkbox is ticked.
  Existing regression commands include
  `uv run pytest scripts/tests/test_link_opencode_auth.py scripts/tests/test_opencode_web_start.py scripts/tests/test_coder_agent_start.py scripts/tests/test_setup_gh_credential_helper.py scripts/tests/test_configure_codex.py scripts/tests/test_repair_codex_cbm_hooks_block.py scripts/tests/test_preapprove_claude_workspace.py scripts/tests/test_docker_image_prune.py`.
- Run `uv run pytest scripts/tests/test_agent_runtime_*.py` for the runtime unit
  contracts; container acceptance is explicitly selected with
  `AGENTDEV_RUNTIME_TEST_IMAGE=<tested-tag-and-digest> uv run pytest scripts/tests/test_agent_runtime_acceptance.py`.
  Container tests without that input skip rather than accidentally using an
  unrelated local image; required CI supplies it and rejects an all-skipped run.
- Run ShellCheck on new/changed shell files, the repository Python lint check on
  new Python files, and workflow/Dockerfile/Compose lint via the existing
  pre-commit configuration. Validate actual Compose clone/bind renderings.
- Use the local build's explicit desktop digest for
  `docker build --build-arg FROM_IMAGE=<desktop-tag-and-digest> -f docker/opencode/agent-opencode.Dockerfile -t agent-opencode:local .`;
  run the acceptance harness against that image. CI repeats real acceptance on
  native amd64 and arm64; QEMU-only checks do not close native gates.
- Tasks 15 and 16 are separate external acceptance gates and must retain their
  named closer until actually observed. No provider/model usage is required for
  unit/ordinary container tests; any explicitly authorized model check uses
  `openai/gpt-6.1-sol` and `openai/gpt-6-luna`.
- Run `iwe normalize` and `iwe schema validate`; run `/agentdev:iwe-verify`
  against this plan and its full deltas before Ship merges durable specs.

## Out of scope

- Multiple projects per running container, automatic repository updates,
  destructive checkout repair, and ownership migration of existing user state.
- Shared credentials across different numeric identity cohorts; shared session,
  home, keyring, or Docker databases between project containers.
- Interactive GitHub-login persistence/sharing, SSH-agent/key provisioning,
  bundled reverse proxy/TLS, Docker MCP gateway/Desktop secrets integration,
  host Docker sockets, and remote Docker engines.
- Claude Remote Control autostart, changing existing Coder/Dev Containers
  defaults, catalog hot reload without restart, and a new bare-metal installer.
- Upgrading CBM to bypass a failed feasibility gate, promising concurrent
  upstream credential-write safety, or redesigning the existing firewall policy.

## Key references

Verified anchor points (line numbers as of 2026-10-17):

- `docker/desktop/agent-desktop.Dockerfile:41-68` — build-time Ansible and
  immutable catalog; `:73-86` — WORKDIR, copied launchers, entrypoint/CMD.
- `.dockerignore:6-11` — ignored Git, user state, devcontainer, and scratch
  sources.
- `.devcontainer/devcontainer.json:12-18` — feature-managed DinD/SSH; `:20-50` —
  runtime environment; `:60-108` — per-instance mounts including OpenCode.
- `.devcontainer/scripts/postCreateCommand.sh:7-47` — ownership handling;
  `:56-68` — Claude link/CBM ordering; `:72-97` — auth, uv, catalog setup.
- `.devcontainer/scripts/postStartCommand.sh:9-31` — current service and
  auth/client startup order.
- `.devcontainer/scripts/postAttachCommand.sh:8-16` — indexing, uv sync,
  checkout catalog registration.
- `.devcontainer/scripts/link-codex-auth.sh:19-31` — hardcoded root credential
  paths and link repair.
- `.devcontainer/scripts/link-opencode-auth.sh:8-21` — overridable auth/data
  roots and migration.
- `.devcontainer/scripts/codebase-memory-mcp-install.sh:22-28` — cache and
  install paths; `:54-82` — symlink restoration and native installation.
- `.devcontainer/scripts/codebase-memory-mcp-start.sh:9-19` — required
  environment, detached daemon, initial index.
- `.devcontainer/scripts/setup-keyring.sh:31-35` — checkout-relative environment
  file and user keyring; `:66-82` — non-destructive initialization; `:111-135` —
  background services/readiness.
- `.devcontainer/scripts/setup-gh-credential-helper.sh:7-30` — keyring
  environment and existing-helper-preserving GitHub setup.
- `.devcontainer/scripts/uv-sync.sh:16-32` — managed `.venv` migration and
  unconditional sync.
- `.devcontainer/scripts/setup-pre-commit.sh:8-20` — skip and hook setup/error
  behavior.
- `.devcontainer/scripts/opencode-web-start.sh:12-48` — workspace link,
  password-gated binding and Coder tmux adapter.
- `.devcontainer/scripts/coder-agent-start.sh:9-21` —
  prune/helper/OpenCode/Remote Control ordering.
- `.devcontainer/scripts/docker-image-prune.sh:12-20` — nonfatal 72-hour image
  prune.
- `.devcontainer/scripts/configure-codex.py:18-26` — policy and HOME/CODEX_HOME
  resolution.
- `docker/desktop/start-xpra.sh:188-244` — foreground/background mode, lifecycle
  checks, bind and D-Bus options; `:251-278` — launch paths.
- `ansible/roles/install_docker/tasks/main.yml:34-63` — Docker packages and 10
  GB BuildKit policy.
- `ansible/roles/devcontainer_firewall/files/init-firewall.sh:14-33` — allowlist
  and rule flush; `:123-163` — DROP/IPv6/self-check policy.
- `ansible/roles/agentic_tools/defaults/main.yml:75-86` — catalog location and
  staged trees.
- `ansible/roles/agentic_tools/tasks/main.yml:23-37` — global CLIs in
  /usr/local.
- `ansible/roles/agentic_tools/tasks/install_catalog.yml:85-145` — Codex agents
  and root OpenCode bridge config.
- `ansible/roles/github_cli/tasks/main.yml:43-49` — baked gh wrapper; `:94-123`
  — user-home gh-stack registration.
- `ansible/roles/dev_tools/defaults/main.yml:58-69` — shipped CBM
  version/checksums.
- `.github/workflows/ci.yml:146-158` — desktop build with same-run base digest;
  `:166-197` — manifest merge; `:246-302` — current acceptance/completion gate.
- `.github/actions/paths-filter/action.yml:35-48` — image-build input filter.
- `.github/actions/docker/build-push-action/action.yml:57-95` — per-arch digest
  publishing/artifacts.
- `.github/actions/docker/multiarch-merge/action.yml:67-120` — manifest and
  pinned output.
- `.github/actions/docker/metadata-action/action.yml:50-59` — existing
  publication tag conventions.
- `.github/renovate.json:5-32` — post-upgrade filters and Compose pin discovery;
  `:42-49` — current image grouping.
- `docs/knowledge/data/spec/catalog-lifecycle.md:20-134` — current catalog
  installation and shared-agent-auth scope.
- `docs/knowledge/data/spec/image-pinning.md:16-65` — digest policy and pin-loop
  avoidance.
- `docs/knowledge/data/architecture/nested-docker-provisioning.md:21-39` —
  feature-owned DinD decision.
- `README.md:25-69` — current images, adoption, and digest policy.
