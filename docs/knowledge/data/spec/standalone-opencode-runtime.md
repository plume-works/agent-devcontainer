---
type: spec
description: The agent-opencode image runs one persistent project without Coder or a Dev Containers client, under a configurable non-root identity, with supervised bounded recovery, a latched failed or degraded state with explicit retry, and browser access only through an external proxy.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-28T12:00:00Z
sources:
- resource: .devcontainer/scripts/runtime-supervisor.py
- resource: .devcontainer/scripts/runtime-remote-control.sh
- resource: .devcontainer/scripts/runtime-bootstrap.sh
- resource: .devcontainer/scripts/runtime-workspace.sh
- resource: .devcontainer/scripts/runtime-health.sh
- resource: .devcontainer/scripts/runtime-docker.sh
- resource: .devcontainer/scripts/runtime-firewall.sh
- resource: .devcontainer/scripts/setup-pre-commit.sh
- resource: docker/opencode/agent-opencode.Dockerfile
- resource: docker/opencode/supervisord.conf
- resource: compose.opencode.yml
- resource: compose.opencode.bind.yml
---

# Standalone OpenCode runtime

The single-project runtime of the `agent-opencode` image, for the [Standalone
OpenCode container](../features/standalone-opencode-container.md) feature. Its
design is [Standalone OpenCode
runtime](../architecture/standalone-opencode-runtime.md). [OpenCode
web](opencode-web.md), [Devcontainer Git
credentials](devcontainer-git-credentials.md), and [Devcontainer Docker
storage](devcontainer-docker-storage.md) keep their integration-specific
requirements; the standalone requirements below do not change Coder's
tmux/failure semantics.

## Requirements

### Requirement: a dedicated image owns a single-project runtime

`ghcr.io/plume-works/agent-opencode` SHALL derive from the corresponding digest
of `agent-desktop`, provide linux/amd64 and linux/arm64 images, and start its
environment without Coder, a Dev Containers client, or project scaffolding. It
SHALL keep Claude Code and Codex available without autostarting them, except
Claude Remote Control when `AGENTDEV_CLAUDE_RC_MODE` opts in, and SHALL omit
Docker MCP gateway integration.

#### Scenario: an ordinary checkout is mounted

- **WHEN** an operator starts the dedicated image with valid required
  configuration
- **THEN** it prepares that single project and starts OpenCode and its required
  services using image-owned shared helpers.

#### Scenario: the existing image is used

- **WHEN** an existing consumer starts agent-desktop or runs its devcontainer
  hooks
- **THEN** its command defaults, Coder integration, opt-outs, and lifecycle
  failure semantics remain compatible.

### Requirement: runtime identity preserves workspace and credential ownership

Agent tools SHALL run with configured numeric UID/GID, default 1000:1000, and
passwordless sudo. DinD and privileged initialization SHALL have the permissions
they require. Containers sharing an agent-auth volume SHALL use the same numeric
UID/GID. Initialization SHALL NOT recursively change workspace/ancestor or
populated shared-auth ownership and SHALL reject incompatible state explicitly.

#### Scenario: a custom identity starts

- **WHEN** writable instance volumes and shared-auth ownership match the
  configured IDs
- **THEN** agent tools, caches, client configuration, and sudo work as that user
  without access to root's private home.

#### Scenario: shared ownership is incompatible

- **WHEN** an existing auth volume belongs to another identity
- **THEN** startup fails without changing its ownership or credential content.

### Requirement: startup prepares or reuses one workspace

The runtime SHALL support a bind-mounted checkout or first clone into an empty
persistent workspace, defaulting to /workspaces/project. It SHALL preserve an
existing checkout without fetch, pull, reset, clean, branch switching, or
ownership migration. It SHALL authenticate supported GitHub HTTPS operations
with injected GH_TOKEN/GITHUB_TOKEN without storing those tokens. It SHALL run
matching uv synchronization, register pre-commit's Git hook scripts without
building hook environments, and submit a background CBM index request for the
workspace. None of these SHALL delay OpenCode, and their failure SHALL mark the
runtime degraded. A checkout that cannot be used SHALL latch the runtime failed.

#### Scenario: the first clone is private

- **WHEN** an empty destination, repository URL, and valid injected token are
  supplied
- **THEN** startup configures noninteractive HTTPS authentication before cloning
  and prepares the checkout without logging the token.

#### Scenario: a dirty checkout restarts

- **WHEN** the workspace has local edits and a selected branch
- **THEN** startup preserves the branch and edits, performs only the supported
  project preparation, and does not automatically contact Git remotes.

#### Scenario: the checkout cannot be used

- **WHEN** required worktree metadata is absent, a nonempty destination is
  invalid, or the clone fails
- **THEN** the runtime latches failed, records the cause, keeps OpenCode
  unavailable, and does not restart or rerun preparation.

#### Scenario: optional preparation fails

- **WHEN** a custom hook conflicts, uv synchronization fails, catalog
  registration fails, or CBM rejects the index request
- **THEN** OpenCode starts and serves, and the runtime reports degraded, naming
  the failed step and its retry command.

#### Scenario: hook environments need the network

- **WHEN** the project's pre-commit hooks would download toolchains or packages
  to build their environments
- **THEN** startup registers the hook scripts without building any environment
  and contacts no hook source.

### Requirement: state survives replacement without cross-project session sharing

The runtime SHALL persist workspace, instance home/configuration, keyrings,
caches/environments, OpenCode provider logins and sessions, and nested Docker
storage. Only Claude and Codex provider credentials SHALL be shared across
project containers; OpenCode provider logins SHALL stay with the instance.
Startup SHALL repair the shared credential links and reconcile managed
client/catalog configuration after mounts on every container start while
preserving unrelated settings and session data. It SHALL NOT add shared
interactive GitHub-login storage.

#### Scenario: an image is upgraded with existing volumes

- **WHEN** a newer image starts against compatible persisted state
- **THEN** required managed configuration is current and provider logins,
  sessions, and unrelated user configuration remain usable.

#### Scenario: two project containers run

- **WHEN** same-ID containers mount the same agent-auth volume and different
  instance volumes
- **THEN** they see shared Claude and Codex credentials but have independent
  OpenCode logins, sessions, keyring databases, caches, and Docker engines.

### Requirement: services have supervised bounded recovery

The runtime SHALL supervise OpenCode, DinD, CBM, D-Bus/keyring, enabled Xpra,
and enabled Remote Control with readiness probes, bounded startup, bounded
per-service retries/backoff, and orderly termination. It SHALL detect actual
daemon failure even when the public tool daemonizes, mark dependency outages
unready, and recover affected clients coherently. OpenCode and D-Bus/keyring
SHALL be core services; DinD, CBM, Xpra, and Remote Control SHALL be optional,
and OpenCode SHALL NOT wait for Xpra. A core service exhausting its budget SHALL
latch the runtime failed; an optional one SHALL mark it degraded while OpenCode
keeps serving. With `AGENTDEV_STRICT_STARTUP=true`, every optional failure SHALL
be treated as a core failure. PID 1 SHALL keep running in both states and SHALL
exit nonzero only when its controller or supervisord fails. Xpra SHALL start by
default with an explicit disable option.

#### Scenario: a running service fails

- **WHEN** a supervised process exits or fails readiness
- **THEN** the runtime becomes unready and restarts that service within its
  recovery budget without duplicating daemons or rerunning project mutation
  unnecessarily.

#### Scenario: a core service keeps failing

- **WHEN** OpenCode or D-Bus/keyring exhausts its bounded recovery budget
- **THEN** the runtime latches failed, records the cause, and keeps PID 1
  running without restarting the container.

#### Scenario: an optional service keeps failing

- **WHEN** DinD, CBM, Xpra, or Remote Control exhausts its bounded recovery
  budget without strict startup
- **THEN** OpenCode keeps serving and the runtime reports degraded, naming that
  service.

#### Scenario: strict startup is selected

- **WHEN** `AGENTDEV_STRICT_STARTUP=true` and any optional service or
  preparation step fails
- **THEN** the runtime latches failed and OpenCode is not served.

#### Scenario: the controller fails

- **WHEN** the supervisor's controller or supervisord itself terminates
  unexpectedly
- **THEN** PID 1 exits nonzero, and the container's restart policy applies.

#### Scenario: the container is stopped

- **WHEN** PID 1 receives SIGTERM
- **THEN** it stops managed clients and services in dependency order, bounds
  shutdown, and reaps remaining processes.

### Requirement: runtime state is reported, persisted, and retried explicitly

The runtime SHALL report one state, `pending`, `ready`, `degraded`, or `failed`,
with each component's status, through `runtime-health.sh status`. Container
health SHALL be healthy only while a live controller reports `ready` and the
core probes pass. Every latched failure SHALL write a bounded record to the home
volume: startup ID, phase, command, exit status, output tail, and time. Startup
SHALL NOT delete that record. A failed or degraded runtime SHALL resume only
through an explicit `runtime-supervisor.py retry`, never by an automatic rerun
of preparation. Boolean settings SHALL accept only documented true and false
spellings, and counts and deadlines SHALL be positive; any other value SHALL
latch a configuration failure naming the variable.

#### Scenario: a failure is inspected later

- **WHEN** an operator inspects a latched runtime, including after a container
  restart or replacement on the same volumes
- **THEN** the original failure record is present and unchanged, and `status`
  names it and its retry command.

#### Scenario: the controller stops reporting

- **WHEN** the controller's heartbeat is older than three health intervals
- **THEN** container health reports unhealthy regardless of the last published
  state.

#### Scenario: an operator retries

- **WHEN** `runtime-supervisor.py retry` runs after the cause is removed
- **THEN** the runtime resumes from the failed component in the same container
  and reports ready on success.

#### Scenario: a boolean is spelled literally

- **WHEN** `AGENTDEV_SKIP_XPRA=false` is set
- **THEN** Xpra starts as if the variable were unset.

### Requirement: browser access uses an external proxy

Supported Compose deployments SHALL publish no host ports and SHALL connect to
an operator-provided proxy network. OpenCode SHALL require a nonempty server
password and bind container port 4096 on a network-reachable interface. Enabled
Xpra SHALL serve port 14500 and SHALL require `XPRA_PASSWORD` for every session,
read from its environment rather than its command line; the runtime SHALL latch
a configuration failure before the bootstrap when Xpra is enabled and no
nonempty `XPRA_PASSWORD` is set. Devcontainer and Coder starts SHALL NOT require
it. OpenCode readiness SHALL be an authenticated API response and SHALL NOT be
inferred from a response that does not require the password.

#### Scenario: a password is missing

- **WHEN** the standalone runtime has no nonempty OpenCode server password
- **THEN** configuration validation fails instead of exposing an unauthenticated
  service or a silently unreachable loopback listener.

#### Scenario: Xpra is enabled without its password

- **WHEN** the standalone runtime starts with `AGENTDEV_SKIP_XPRA` empty and no
  nonempty `XPRA_PASSWORD`
- **THEN** it latches failed before the bootstrap, naming `XPRA_PASSWORD` and
  `AGENTDEV_SKIP_XPRA=1`, without restarting the container.

#### Scenario: a peer on the proxy network connects to Xpra directly

- **WHEN** another container on the proxy network opens an Xpra session on port
  14500
- **THEN** the session is refused without the correct `XPRA_PASSWORD` and
  accepted with it.

#### Scenario: proxy requests reach the runtime

- **WHEN** an authorized user accesses the configured proxy routes
- **THEN** OpenCode API/assets and Xpra HTTP/WebSocket work, and OpenCode
  rejects API requests lacking its password.

### Requirement: nested Docker and opt-in firewall retain their policies

The runtime SHALL operate its own persisted DinD engine through a private Unix
socket, without a host socket mount or Docker TCP listener. It SHALL retain 10
GB BuildKit GC and startup pruning of unused images older than 72 hours, with
prune errors nonfatal. The egress firewall SHALL remain opt-in; enabled
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
