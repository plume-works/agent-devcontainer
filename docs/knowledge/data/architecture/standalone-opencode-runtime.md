---
type: architecture
description: agent-opencode runs supervisord in-process as PID 1 behind a root bootstrap; a controller event listener sequences services on readiness, recovers each within a bounded budget, refreshes dependent clients, and exits the container nonzero when recovery is exhausted.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-19T16:00:00Z
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

OpenCode logins stay per project container. OpenCode v2 keeps them in
`~/.local/share/opencode/opencode.db` on the instance home volume, so they
survive replacement and upgrade, and each project container logs in once. The
auth volume holds no OpenCode directory. Two ways to share them were rejected:

- Sharing the database would share sessions too, since they live in it.
- Sharing `auth.json` would carry only a stale first login: v2 imports it once
  and never writes it.

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
exit `1` after a terminal failure while supervisord remains the process that
reaps every orphan. A wrapper shell or an init shim would take PID 1 away from
supervisord.

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

## Ordering and readiness

Services start in this order, each gated on `runtime-health.sh <service>`
passing within the service-start deadline: `dockerd`, `dbus`, `keyring`, the
`prepare` one-shot, `cbm`, the `index` one-shot, `xpra`, then `opencode`.
One-shots run once per container start under the preparation deadline, and a
nonzero exit or timeout is terminal, so OpenCode never starts on a failed
preparation. Aggregate readiness is the file `/run/agentdev/ready`, which the
image healthcheck reads. It is removed for the length of any recovery.

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
- Exhaustion writes the reason to `/run/agentdev/failed` and asks supervisord to
  shut down; PID 1 then exits `1`.

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
