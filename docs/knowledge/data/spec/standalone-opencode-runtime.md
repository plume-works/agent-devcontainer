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
