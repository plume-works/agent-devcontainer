---
type: architecture
description: agent-opencode runs supervisord in-process as PID 1 behind a root bootstrap; a controller event listener starts OpenCode on a core path with optional work around it, recovers each service within a bounded budget, degrades on optional failures, and latches failed on core ones until an explicit retry.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-23T21:45:57Z
sources:
- resource: .devcontainer/scripts/runtime-supervisor.py
- resource: .devcontainer/scripts/runtime-health.sh
- resource: docker/opencode/supervisord.conf
- resource: scripts/tests/test_agent_runtime_supervision.py
- resource: .devcontainer/scripts/runtime-docker.sh
- resource: scripts/tests/test_agent_runtime_docker.py
- resource: .devcontainer/scripts/runtime-bootstrap.sh
- resource: .devcontainer/scripts/runtime-workspace.sh
- resource: .devcontainer/scripts/setup-agent-state.sh
- resource: .devcontainer/scripts/runtime-firewall.sh
- resource: docker/opencode/agent-opencode.Dockerfile
- resource: docker/desktop/start-xpra.sh
- resource: ansible/roles/agentic_tools/defaults/main.yml
- resource: compose.opencode.yml
- resource: scripts/tests/test_agent_runtime_acceptance.py
---

# Standalone OpenCode runtime

`agent-opencode` is a separate image layered on `agent-desktop`. It is not a new
default for the desktop image, whose entrypoint, Dev Containers hooks, and Coder
start are unchanged.

## Shared helpers, not shared hooks

The image bakes `.devcontainer/scripts/` into `/opt/agentdev-runtime` and calls
the same primitives the devcontainer hooks call: `setup-agent-state.sh`,
`runtime-paths.sh`, the CBM, keyring, and Git helpers. Every path those
primitives touch is overridable, and the defaults are the devcontainer's root
layout. `AGENTDEV_RUNTIME_MODE=standalone` makes every step fatal where a hook
logs and continues.

Running the lifecycle hooks unchanged was rejected. They assume root, a checkout
that contains this repository's scaffolding, and the Dev Containers client's
call order. Copying the whole checkout into the image was rejected for the same
reason. The catalog stays the immutable `/opt/agentdev` tree, and a checkout
that ships complete manifests overrides it per start.

## Identity and state

`runtime-bootstrap.sh` creates `agent` from `AGENTDEV_UID`/`AGENTDEV_GID` at
every container start, because a fresh container has no such account and the IDs
are deployment settings. The image deletes the stock UID 1000 account and does
not create `/home/agent`, so a fresh home volume starts empty, without Docker
copying files into it, and is initialized after mounts.

Only Claude and Codex credentials are shared, through one auth volume per
UID/GID cohort. Sharing a whole home or agent directory was rejected: sessions,
configuration, keyrings, and caches record per-project state, and two containers
writing them would corrupt each other. Sharing across cohorts was rejected
because it would mean rewriting another running container's file ownership.

OpenCode logins stay per project container. OpenCode 2.0.32
(`agentic_tools_opencode_version`) keeps them in
`~/.local/share/opencode/opencode.db` on the instance home volume, so they
survive replacement and upgrade, and each project container logs in once. The
auth volume holds no OpenCode directory. Two ways to share them were rejected:

- Sharing the database would share sessions too, since they live in it.
- Sharing `auth.json` would carry only a stale first login: OpenCode 2.0.32
  imports it once and never writes it.

## Ingress authentication

The proxy network is shared, so the proxy cannot be the only access boundary:
any peer on it reaches the container's ports directly. Each service therefore
authenticates on its own. OpenCode requires `OPENCODE_SERVER_PASSWORD`, and Xpra
requires `XPRA_PASSWORD` through its `env` auth module, which keeps the secret
off the command line. PID 1 refuses to proceed with Xpra enabled and no
password, before the bootstrap, latching a configuration failure rather than
failing Xpra's recovery budget later. Devcontainer and Coder starts bind Xpra to
loopback and need no password.

Two alternatives were rejected. Requiring `ENABLE_FIREWALL` with trusted proxy
CIDRs whenever Xpra runs would couple desktop access to the opt-in egress
firewall. Documenting that the proxy network must have no other members leaves
the default deployment open.

## OpenCode lifetime

Standalone runs `opencode serve` in the foreground under supervisord, keeping
`DISPLAY` for the graphical tools it spawns; `serve` and `web` start the same
server, but `serve` opens no browser. The Coder start keeps its tmux session,
which exists to survive the Coder agent's own restarts. In a container whose PID
1 already supervises, tmux would hide crashes from the controller and outlive a
stop.

## Process model

PID 1 is `runtime-supervisor.py run`. It runs `runtime-bootstrap.sh` as root,
which creates the runtime account before any program that names it is
configured. It then calls `supervisor.supervisord.main()` in the same process.
supervisord's own `main()` always exits `0`. Running it in-process lets PID 1
exit `1` when the controller fails while supervisord remains the process that
reaps every orphan. A wrapper shell or an init shim would take PID 1 away from
supervisord. A watchdog thread in PID 1 notices a controller listener that died
outside a shutdown and stops supervisord, so that crash ends the container.

Every program is `autostart=false`, `startretries=0`, `autorestart=false`:
supervisord only spawns, signals, and reaps. The `controller` event listener
owns all ordering and recovery. It answers the listener protocol on its main
thread and runs the controller on a worker thread, so a long recovery never
stalls event delivery. Program output goes to supervisord's stdout and
`docker logs`; the listener logs to stderr because its stdout carries the
protocol.

## Startup order

Bootstrap and the opt-in firewall run as root before supervisord starts, so the
firewall's rule flush can never erase rules `dockerd` installs later. The
controller then starts the services in dependency order.

## Core path and optional work

The core path is `dbus`, `keyring`, and the `prepare` one-shot (checkout, Claude
and Codex login links, agent policy), then `opencode`. The other components are
optional:

- `config` registers the catalog and then the CBM client configuration. It runs
  before OpenCode, which reads both when it starts.
- `cbm` also starts before OpenCode: an MCP client that finds no daemon starts a
  session-managed one that the runtime cannot adopt as permanent (see [CBM
  daemon lifecycle](cbm-daemon-lifecycle.md)).
- `xpra` launches together with `opencode`, and neither waits for the other.
- `dockerd`, the `prune` image prune, the `project` one-shot (uv sync and
  pre-commit hook registration), and the `index` request follow OpenCode.

An optional failure marks the runtime `degraded`, and OpenCode keeps serving. A
component whose dependency failed is `blocked` until that dependency is retried.
`AGENTDEV_STRICT_STARTUP=true` treats every optional component as core.

Starting OpenCode last, behind every service, was rejected. A broken uv sync or
nested Docker would then keep the agent unreachable, and a large index would
delay every start.

## Readiness

Each service is gated on `runtime-health.sh <service>` passing within the
service-start deadline; one-shots run once per container start under the
preparation deadline. The controller publishes `/run/agentdev/state.json`
(`pending`, `ready`, `degraded`, or `failed`, with each component's status) and
refreshes its heartbeat every interval from a separate thread, so a long phase
never looks like a dead controller. `runtime-health.sh ready`, the image
healthcheck, passes only when that heartbeat is younger than three intervals,
the state is `ready`, and the `dbus`, `keyring`, and `opencode` probes pass at
that moment. The healthcheck's start period covers the core path alone.

## Failure latch

A failure the runtime cannot recover from latches it `failed`: a failed
bootstrap, an invalid setting or missing `XPRA_PASSWORD`, a failed core phase,
or a core service exhausting its budget. PID 1 and supervisord stay up, OpenCode
is stopped, nothing is restarted or rerun, and readiness stays withdrawn. Each
program runs under `runtime-supervisor.py exec`, which streams its output and
keeps its command, exit status, and last 200 lines. Every failure writes those,
the start's ID, and the time to `last-failure.json` on the home volume. Startup
never deletes that record. A failure before the home volume is validated goes to
stderr only.

`runtime-supervisor.py retry` resumes from the failed component in the same
container. Before supervisord starts, PID 1 itself waits for the request and
reruns the configuration check and bootstrap.

Exiting PID 1 nonzero on every unrecoverable failure was rejected. Under
Compose's `restart: unless-stopped`, that reruns non-transactional preparation
against the same volumes without bound. PID 1 exits nonzero only when the
controller or supervisord fails, which leaves the restart policy for crashes.

## Recovery

- A process exit, or `AGENTDEV_PROBE_FAILURES` consecutive failed probes, counts
  against that service's own budget (`AGENTDEV_RECOVERY_ATTEMPTS`, backoff
  doubling from `AGENTDEV_RECOVERY_BACKOFF`). A process that is running but
  never passes its probe is therefore not healthy.
- The budget resets only after `AGENTDEV_HEALTHY_RESET` seconds of continuous
  health; startup failures and post-RUNNING failures share the same budget.
- When a dependency recovers, its clients are restarted outside their own
  budgets. A replaced session bus takes `gnome-keyring` down with it, so `dbus`
  refreshes `keyring` and `xpra`. A replaced CBM daemon ends OpenCode's stdio
  MCP clients (see [CBM daemon lifecycle](cbm-daemon-lifecycle.md)), so `cbm`
  refreshes `opencode`.
- Before restarting a service, the controller kills whatever is left of the
  failed process's group: supervisord signals a group only on an orderly stop.
  Xpra starts its X server in a separate session, beyond that group, so
  `start-xpra.sh --supervised` also stops a leftover Xpra X server holding the
  display when no live session owns it.
- Exhaustion degrades the runtime for an optional service and latches it for a
  core one.

## Shutdown

supervisord stops program groups one at a time from the highest priority down,
waiting for each. Priorities put `opencode` first, then `cbm`, `xpra`,
`keyring`, `dbus`, and `dockerd` last. The controller has the highest priority
of all, so it is gone before any service stops and never mistakes shutdown for
failure. `stopasgroup`/`killasgroup` with `AGENTDEV_STOP_TIMEOUT` bound each
stop and take a program's whole process group with it.

## Nested Docker

The standalone image runs its own engine instead of the Dev Containers feature's
(see [Nested Docker provisioning](nested-docker-provisioning.md) for the
devcontainer's decision). `runtime-docker.sh run` execs one root `dockerd` on
`/var/run/docker.sock` with `--group docker`; the runtime user reaches it
through that group. A `hosts` key in `daemon.json` is refused: dockerd rejects
it beside `--host`, and any extra listener would widen the engine's reach.

With no system containerd socket present, dockerd supervises its own containerd
and roots it at `/var/lib/docker/containerd/daemon`. The containerd image
store's content and snapshots therefore live inside `/var/lib/docker`, and that
one volume holds everything the engine persists. The engine is not reliable on
the container's own overlay filesystem, so the script refuses to start unless
`/var/lib/docker` is a separate mount.
