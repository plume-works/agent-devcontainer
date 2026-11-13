---
type: spec
description: The agentdev-deploy image runs one persistent project without Coder or a Dev Containers client, under a configurable non-root identity, with supervised bounded recovery, a latched failed or degraded state with explicit retry, and browser access only through an external proxy.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/supervisor.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/remote_control.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/workspace.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/health.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/docker.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/firewall.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/project.py
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: docker/deploy/supervisord.conf
- resource: compose.opencode.yml
- resource: compose.opencode.bind.yml
- resource: py_packages/agentdev_runtime/agentdev_runtime/opencode.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/settings.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/xpra.py
---

# Standalone OpenCode runtime

The single-project runtime of the `agentdev-deploy` image. [OpenCode
web](opencode-web.md), [Devcontainer Git
credentials](devcontainer-git-credentials.md), and [Devcontainer Docker
storage](devcontainer-docker-storage.md) keep their integration-specific
requirements; the standalone requirements below do not change Coder's
tmux/failure semantics.

## Requirements

### Requirement: a dedicated image owns a single-project runtime

`ghcr.io/plume-works/agentdev-deploy` SHALL derive from the corresponding digest
of `agentdev-base`, provide linux/amd64 and linux/arm64 images, and start its
environment without Coder, a Dev Containers client, or project scaffolding. It
SHALL keep Claude Code available without autostarting it, except Claude Remote
Control when `AGENTDEV_CLAUDE_RC_MODE` opts in, and SHALL NOT install Codex.

#### Scenario: an ordinary checkout is mounted

- **WHEN** an operator starts the dedicated image with valid required
  configuration
- **THEN** it prepares that single project and starts OpenCode and its required
  services using image-owned shared helpers.

#### Scenario: the base image is used

- **WHEN** an existing consumer starts `agentdev-base` or runs its own copied
  devcontainer hooks on it
- **THEN** it keeps the lifecycle-neutral base's command defaults, Coder
  integration, opt-outs, and lifecycle failure semantics, and no deploy runtime
  starts.

### Requirement: runtime identity preserves workspace and credential ownership

Agent tools SHALL run with configured numeric UID/GID, default 1000:1000, and
passwordless sudo. DinD and privileged initialization SHALL have the permissions
they require. Containers sharing an agent-auth volume SHALL use the same numeric
UID/GID. Initialization SHALL NOT recursively change workspace/ancestor or
populated shared-auth ownership and SHALL reject incompatible state explicitly.
The image SHALL hold no account at the default UID and no home directory; the
root bootstrap SHALL create the runtime account from `AGENTDEV_UID` and
`AGENTDEV_GID` at every container start, without creating a home directory, so a
fresh home volume starts empty.

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
matching uv synchronization and register pre-commit's Git hook scripts without
building hook environments. None of these SHALL delay OpenCode, and their
failure SHALL mark the runtime degraded. A checkout that cannot be used SHALL
latch the runtime failed.

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

- **WHEN** a custom hook conflicts, uv synchronization fails, or catalog
  registration fails
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
storage. Only Claude provider credentials SHALL be shared across project
containers; OpenCode provider logins SHALL stay with the instance. Startup SHALL
repair the shared credential links and reconcile managed client/catalog
configuration after mounts on every container start while preserving unrelated
settings and session data. It SHALL NOT add shared interactive GitHub-login
storage.

#### Scenario: an image is upgraded with existing volumes

- **WHEN** a newer image starts against compatible persisted state
- **THEN** required managed configuration is current and provider logins,
  sessions, and unrelated user configuration remain usable.

#### Scenario: two project containers run

- **WHEN** same-ID containers mount the same agent-auth volume and different
  instance volumes
- **THEN** they see shared Claude credentials but have independent OpenCode
  logins, sessions, keyring databases, caches, and Docker engines.

### Requirement: services have supervised bounded recovery

The runtime SHALL supervise OpenCode, DinD, D-Bus/keyring, enabled Xpra, and
enabled Remote Control with readiness probes, bounded startup, bounded
per-service retries/backoff, and orderly termination. It SHALL detect actual
daemon failure even when the public tool daemonizes, mark dependency outages
unready, and recover affected clients coherently. OpenCode and D-Bus/keyring
SHALL be core services; DinD, Xpra, and Remote Control SHALL be optional (Xpra
launches alongside OpenCode, as Requirement: OpenCode starts on the core path
states). OpenCode SHALL run as a supervised foreground `opencode serve` that
keeps `DISPLAY`, not in a tmux session. A core service exhausting its budget
SHALL latch the runtime failed; an optional one SHALL mark it degraded while
OpenCode keeps serving. With `AGENTDEV_STRICT_STARTUP=true`, every optional
failure other than a Docker garbage-collection error SHALL be treated as a core
failure.

A process exit, or `AGENTDEV_PROBE_FAILURES` consecutive failed probes, SHALL
count against that service's own budget of `AGENTDEV_RECOVERY_ATTEMPTS`
restarts, with backoff doubling from `AGENTDEV_RECOVERY_BACKOFF`; the budget
SHALL reset only after `AGENTDEV_HEALTHY_RESET` seconds of continuous health.
When a dependency recovers, the clients that read it at startup SHALL be
restarted outside their own budgets: `dbus` refreshes `keyring` and `xpra`. When
a client fails while a long-running dependency, walked transitively, fails its
probe, the root-most such dependency SHALL be recovered instead of the client,
without waiting for the probe-failure count. Running services SHALL stay watched
while a one-shot phase runs. PID 1 SHALL keep running in both states and SHALL
exit nonzero only when its controller or supervisord fails. Xpra SHALL start by
default with an explicit disable option.

#### Scenario: a running service fails

- **WHEN** a supervised process exits or fails readiness
- **THEN** the runtime becomes unready and restarts that service within its
  recovery budget without duplicating daemons or rerunning project mutation
  unnecessarily.

#### Scenario: a client fails because its dependency is down

- **WHEN** `keyring` exits while `dbus` is running but fails its probe
- **THEN** the runtime recovers `dbus`, restarts `keyring` through `dbus`'s
  refresh without charging `keyring`'s budget, and does not latch.

#### Scenario: a core service keeps failing

- **WHEN** OpenCode or D-Bus/keyring exhausts its bounded recovery budget
- **THEN** the runtime latches failed, records the cause, and keeps PID 1
  running without restarting the container.

#### Scenario: an optional service keeps failing

- **WHEN** DinD, Xpra, or Remote Control exhausts its bounded recovery budget
  without strict startup
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
with each component's status, through `agentdev-runtime health status`; a
component whose dependency has not settled SHALL report `blocked` until that
dependency is retried. Container health SHALL be healthy only while a live
controller reports `ready` and the core probes pass. Every program's output
SHALL reach the container log. A latch SHALL stop OpenCode, even when OpenCode
is still running. Every latched failure after the bootstrap SHALL write a
bounded record to the home volume: startup ID, phase, command, exit status,
output tail from the failed attempt only, and time. A configuration or bootstrap
failure, which comes before the home volume is validated, SHALL be written to
stderr only. Startup SHALL NOT delete the record. A failed or degraded runtime
SHALL resume only through an explicit `agentdev-runtime supervisor retry`, never
by an automatic rerun of preparation. A successful retry SHALL restart each
client already serving that reads the retried component at startup: a retried
`config` restarts `opencode`. A retry of a failed bootstrap SHALL rerun the
configuration check and the bootstrap, after every process the failed bootstrap
started has been killed. Boolean settings SHALL accept only documented true and
false spellings, and counts and deadlines SHALL be positive; any other value
SHALL latch a configuration failure naming the variable.

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

- **WHEN** `agentdev-runtime supervisor retry` runs after the cause is removed
- **THEN** the runtime resumes from the failed component in the same container
  and reports ready on success.

#### Scenario: a boolean is spelled literally

- **WHEN** `AGENTDEV_SKIP_XPRA=false` is set
- **THEN** Xpra starts as if the variable were unset.

### Requirement: OpenCode starts on the core path

The runtime SHALL start `dbus`, `keyring`, and the `prepare` one-shot, then
OpenCode, launching Xpra alongside OpenCode. Catalog registration (`config`)
SHALL finish before OpenCode starts, because OpenCode reads it at startup.
Nested Docker, its garbage collector, and the `project` one-shot SHALL start
only after OpenCode is ready, and Remote Control after `prepare`.

#### Scenario: uv synchronization is slow

- **WHEN** the project's `uv sync` takes minutes
- **THEN** OpenCode is already serving while it runs.

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

#### Scenario: proxy requests reach the runtime

- **WHEN** an authorized user accesses the configured proxy routes
- **THEN** OpenCode API/assets and Xpra HTTP/WebSocket work, and OpenCode
  rejects API requests lacking its password.

### Requirement: the Compose deployment owns per-project volumes and one shared auth volume

`compose.opencode.yml` SHALL create the project's home, Docker, and workspace
volumes per Compose project, and SHALL mount one agent-auth volume whose name is
`AGENTDEV_AUTH_VOLUME`, defaulting to `agentdev-opencode-auth`, so every project
container of one UID/GID cohort shares it.

#### Scenario: two projects are deployed with the default settings

- **WHEN** two Compose projects start from `compose.opencode.yml` without
  `AGENTDEV_AUTH_VOLUME`
- **THEN** each gets its own home, Docker, and workspace volumes, and both mount
  `agentdev-opencode-auth`.

### Requirement: nested Docker and opt-in firewall retain their policies

The runtime SHALL operate its own persisted DinD engine through a private Unix
socket, without a host socket mount or Docker TCP listener: `dockerd` runs as
root on `/var/run/docker.sock` with `--group docker`, and
`agentdev-runtime docker run` SHALL refuse to start it when `daemon.json`
declares a `hosts` listener. It SHALL retain 10 GB BuildKit GC and the hourly
garbage collection of [Devcontainer Docker
storage](devcontainer-docker-storage.md), with every collection error nonfatal.
The egress firewall SHALL remain opt-in; enabled configuration SHALL retain its
allowlist/IPv6 policy and self-checks while supporting explicitly trusted proxy
ingress and nested Docker operation.

#### Scenario: the engine restarts

- **WHEN** the container or nested daemon is replaced using its persistent
  storage
- **THEN** its existing images remain available and builds run as the runtime
  user.

#### Scenario: the engine configuration declares a listener

- **WHEN** `daemon.json` holds a nonempty `hosts` key
- **THEN** `agentdev-runtime docker run` exits non-zero naming the socket the
  engine listens on, and `dockerd` does not start.

#### Scenario: the firewall is enabled

- **WHEN** a valid allowlist and trusted proxy sources are configured
- **THEN** required proxy access and nested builds work, forbidden egress
  remains blocked, and daemon network rules are not erased by startup ordering.

## Rationale

### Shared helpers, not shared hooks

The image installs the `agentdev_runtime` package and calls the same primitives
the Dev Container lifecycle commands call, with every path they touch
overridable and the Dev Container's layout as the default.
`AGENTDEV_RUNTIME_MODE=deploy` makes a step fail where the Dev Container
lifecycle logs and continues. The catalog stays the immutable staged tree, and a
checkout that ships complete manifests overrides it per start.

Rejected:

- **Running the lifecycle hooks unchanged.** They assume root, a checkout that
  contains this repository's scaffolding, and the Dev Containers client's call
  order.
- **Copying the whole checkout into the image.** It carries the same
  assumptions.

### Only Claude credentials are shared, per UID/GID cohort

The account is created at every start because a fresh container has none and its
IDs are deployment settings. One auth volume per UID/GID cohort shares Claude's
credentials; OpenCode logins live in OpenCode's database on the instance home
volume, so each project container logs in once and keeps the login across
replacement and upgrade.

Rejected:

- **Sharing a whole home or agent directory.** Sessions, configuration,
  keyrings, and caches record per-project state, and two containers writing them
  would corrupt each other.
- **Sharing across cohorts.** It would mean rewriting another running
  container's file ownership.
- **Sharing OpenCode's database.** Sessions live in it, so they would be shared
  too.
- **Sharing OpenCode's `auth.json`.** OpenCode v2 keeps logins in its database
  and writes no `auth.json`, so a shared file would carry no login.

### Every service authenticates on its own

The proxy network is shared, so any peer on it reaches the container's ports
directly and the proxy cannot be the only access boundary. OpenCode requires its
server password and Xpra its `env`-module password, which keeps the secret off
the command line; PID 1 checks the Xpra password before the bootstrap, so a
missing one latches a configuration failure instead of spending Xpra's recovery
budget. Dev Container and Coder starts bind Xpra to loopback.

Rejected:

- **Requiring `ENABLE_FIREWALL` with trusted proxy CIDRs whenever Xpra runs.**
  It couples desktop access to the opt-in egress firewall.
- **Documenting that the proxy network must have no other members.** It leaves
  the default deployment open.

### OpenCode runs in the foreground under supervisord

OpenCode v2 starts its server with `serve`, which opens no browser, so `DISPLAY`
stays for the graphical tools OpenCode spawns. The Coder start keeps its tmux
session, which exists to survive the Coder agent's own restarts.

Rejected:

- **tmux in the standalone runtime.** Under a PID 1 that already supervises,
  tmux hides crashes from the controller and outlives a stop.

### supervisord runs in-process as PID 1, and a controller owns order

PID 1 runs the root bootstrap and the opt-in firewall, then supervisord's
`main()` in the same process, so supervisord reaps every orphan while PID 1 can
still exit nonzero when the controller fails, which supervisord's own `main()`
never does. The firewall runs first so its rule flush cannot erase rules
`dockerd` installs later. supervisord only spawns, signals, and reaps; the
`controller` event listener owns ordering and recovery, answering the listener
protocol on one thread and running the controller on another so a long recovery
never stalls event delivery.

Rejected:

- **A wrapper shell or an init shim as PID 1.** It takes PID 1 away from
  supervisord.

### OpenCode first, optional work around it

The core path is the minimum OpenCode needs; everything else degrades the
runtime rather than holding OpenCode back.

Rejected:

- **Starting OpenCode last, behind every service.** A broken uv sync or nested
  Docker would keep the agent unreachable, and a large index would delay every
  start.

### An unrecoverable failure latches instead of exiting

PID 1 and supervisord stay up on a latch, and PID 1 exits nonzero only when the
controller or supervisord fails, which leaves the restart policy for crashes.

Rejected:

- **Exiting PID 1 nonzero on every unrecoverable failure.** Under Compose's
  `restart: unless-stopped`, that reruns non-transactional preparation against
  the same volumes without bound.

### A client failure is charged to its failing dependency

A replaced session bus takes `gnome-keyring` down with it, so a client can fail
before its dependency's probe has failed often enough to count. The client's
failure corroborates the dependency's failed probe, so the controller recovers
the dependency without the debounce. The accepted cost: a dependency that was
only slow to answer is restarted, taking its clients with it.

Rejected:

- **Deferring the client until the next pass confirms the dependency.** A
  waiting client cannot be marked unready without leaving it out of the
  `refresh` restart, so it would read `ready` while down for up to one interval.
- **Not charging the client's budget while its dependency is down.** It still
  restarts the client against a dead dependency, and removes the budget's bound
  on those restarts.
- **Dependency-ordered recovery.** It is the general init-system behaviour the
  controller avoids, and this case does not need it.

### Remote Control is a long-running watcher gated by PID 1

`agentdev-runtime remote-control start` reads an unset mode as `session`, so it
cannot tell "off" from the default; PID 1 leaves the component out when no mode
is set. The usual first start has no claude.ai login yet, so the component waits
for one, checking the credential file's inode, mtime, and size and running
`claude auth status` only when they change. Its tmux server daemonizes outside
the watcher's process group, so a restarted watcher adopts the live session, and
the controller's recovery budget bounds how often Remote Control restarts.

Rejected:

- **A one-shot that skips when there is no login.** It needs an operator step
  after the first `/login`, and nothing would restart a session that exits.
- **Running `claude auth status` on every interval.** It starts a Claude process
  each time.

### Xpra is driven with Xpra 6's command line and both X server names

Xpra 6 rejects `--global-menus` and `--dbus-proxy`, so the runtime passes
neither. Xpra 6 names its X server `Xvfb-for-Xpra-N` where Xpra 3 used
`Xvfb-for-Xpra-:N`; the orphaned-display reclaim matches both, or a crashed
Xpra's X server keeps the display locked.

### Configuration is documented variables, never shell code

The runtime is configured only through the documented variables in
`agentdev_runtime.settings`. The two that name commands,
`AGENTDEV_HEALTH_COMMAND` and `AGENTDEV_BOOTSTRAP_COMMAND`, are split into an
argument list and run without a shell.

Rejected:

- **Command strings a shell evaluates.** Every configured value would become
  shell code, with its quoting and injection hazards.

### The runtime stops at its own container and its expected path

The runtime serves one project and assumes its startup steps work: a failed step
latches for inspection and explicit retry.

Rejected:

- **Several projects in one running container.** Each project gets its own
  container and volumes.
- **Automatic repository updates or destructive checkout repair.** They would
  overwrite the operator's branch and local edits.
- **SSH-agent or key provisioning.** GitHub HTTPS with an injected token covers
  the supported operations.
- **A bundled reverse proxy or TLS.** The operator's proxy owns routing and
  certificates.
- **A host Docker socket or a remote Docker engine.** The runtime operates its
  own nested engine.
- **Staged or transactional startup writes.** A latch with explicit retry
  already keeps a failed step from being rerun blindly.
