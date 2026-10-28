---
type: bug
description: A standalone agent-opencode container whose CBM daemon fails to start stays degraded and Docker-unhealthy through every recovery attempt, the advertised retry, and a container restart, because the leftover rendezvous artifacts under /tmp survive in the writable layer; only recreating the container clears it.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-28T16:49:05Z
sources:
- resource: https://github.com/plume-works/agent-devcontainer/issues/488
- resource: https://github.com/DeusData/codebase-memory-mcp/issues/2162
- resource: .devcontainer/scripts/runtime-cbm.sh
- resource: .devcontainer/scripts/runtime-supervisor.py
- resource: .devcontainer/scripts/runtime-health.sh
- resource: docker/opencode/supervisord.conf
- resource: docker/opencode/agent-opencode.Dockerfile
- resource: docs/knowledge/data/architecture/cbm-daemon-lifecycle.md
---

# Bug: a CBM daemon start failure latches the standalone runtime degraded

## Symptom

In a standalone `agent-opencode` container (agentdev 4.2.0,
`codebase-memory-mcp` 0.12.1), `codebase-memory-mcp daemon start` fails with
`CBM daemon could not start within 30000 ms`. The supervisor's three recovery
attempts fail the same way, the runtime settles in `degraded` with `cbm: failed`
and `index: blocked (waiting for cbm)`, and once the 10-minute health-check
start period ends Docker marks the container `unhealthy`.

`runtime-supervisor.py retry cbm`, the retry the status report advertises, gives
the same result. Afterwards `daemon status` reports `not running`, but
`/tmp/cbm-daemon-1000` still holds `.sock`, `.anc` (the same two-link inode),
`.sock.identity`, and cohort/startup lock artifacts, and nothing is listening on
the endpoint. Nothing reports which condition stops the daemon from starting;
the only message is the generic timeout.

## Reproduction

There is no deterministic recipe. Seen once on image
`ghcr.io/plume-works/agent-opencode:edge@sha256:4ed1952366aa9f746a68df7593ab35f702352cf1abf9f52f9a26c36131afbda9`
(revision `1ab4ebe0`), Docker Engine 29.8.0. The container was not OOM-killed
and Docker had not restarted it.

- `docker restart` on the affected container brings the failure back. The
  rendezvous artifacts keep the same inode numbers across the restart.
- Recreating only the service container from the same image, with every named
  volume (home/cache, workspace, UV, nested Docker, shared auth) kept, clears
  it. The runtime goes `pending` → `ready`, CBM listens on its endpoint, and
  Docker reports `healthy`.
- A second container from the same image and the same Compose config hash stayed
  healthy. Both containers had the same CBM cache and database ownership and
  modes, and SQLite `PRAGMA quick_check` returned `ok` on `_config.db`,
  `activity.db`, and the project database in both. The healthy container had the
  same rendezvous artifacts, with an active CBM listener on `.anc`.

## Root cause

Not established. The persistent CBM cache and databases worked once the
container was replaced, so the blocking state is in the container's writable
layer. The likely culprit is the rendezvous generation under
`/tmp/cbm-daemon-<euid>`. The image does not set `CBM_RUNTIME_DIR`, so the
rendezvous sits in `/tmp`, which `docker restart` keeps.

`runtime-cbm.sh start` uses only `daemon start`, so it cannot see or reclaim a
leftover rendezvous generation. Every recovery attempt and every `retry` repeats
the same call against the same leftover state. The available evidence does not
show which CBM invariant stops `daemon start` from reclaiming the endpoint. The
upstream report DeusData/codebase-memory-mcp#2162 has the same timeout, but no
`reservation_validation` or `listener_handoff` diagnostic was captured here, so
it is unconfirmed whether this is the same race. It is also undecided which
layer should fix it: this runtime or upstream CBM.

## Fix

Not fixed. A fix needs `retry cbm` to do one of two things:

- reclaim a stale or contested rendezvous generation safely and bring the
  runtime back to `ready`;
- or report the exact condition blocking the start, together with a supported
  way to recover.

Restoring health must not require deleting index or credential data. One
direction is to keep CBM's daemon-side diagnostics when a start fails, so the
upstream race can be confirmed or ruled out. Another is to put the rendezvous
somewhere a container restart clears.

## Key references

Verified anchor points (line numbers as of 2026-10-28):

- `.devcontainer/scripts/runtime-cbm.sh:117` — `cmd_start`'s `daemon start`
  call, the only start path; it inspects no rendezvous state
- `.devcontainer/scripts/runtime-cbm.sh:120` —
  `daemon start failed with exit code` log line from the incident
- `.devcontainer/scripts/runtime-cbm.sh:182` — `cmd_run` calls `cmd_start`, so
  every supervised restart repeats it
- `.devcontainer/scripts/runtime-supervisor.py:544` — `restart_until_ready`, the
  bounded recovery that raises `exhausted N recovery attempts`
- `.devcontainer/scripts/runtime-supervisor.py:973` — `retry`, the advertised
  operator retry
- `.devcontainer/scripts/runtime-health.sh:43` — `cbm` readiness probe behind
  the image health check
- `docker/opencode/supervisord.conf:164` — `[program:cbm]` runs
  `runtime-cbm.sh run`, with no `CBM_RUNTIME_DIR` in its environment
- `docker/opencode/agent-opencode.Dockerfile:63` — `HEALTHCHECK` with the
  10-minute start period
