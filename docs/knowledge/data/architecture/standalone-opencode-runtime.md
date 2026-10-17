---
type: architecture
description: agent-opencode runs supervisord in-process as PID 1 behind a root bootstrap; a controller event listener sequences services on readiness, recovers each within a bounded budget, refreshes dependent clients, and exits the container nonzero when recovery is exhausted.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-17T23:30:00Z
sources:
- resource: .devcontainer/scripts/runtime-supervisor.py
- resource: .devcontainer/scripts/runtime-health.sh
- resource: docker/opencode/supervisord.conf
- resource: scripts/tests/test_agent_runtime_supervision.py
- resource: .devcontainer/scripts/runtime-docker.sh
- resource: scripts/tests/test_agent_runtime_docker.py
---

# Standalone OpenCode runtime

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
