---
type: architecture
description: The codebase-memory-mcp daemon is one per account per rendezvous directory; a supervisor drives it only through daemon start/status/stop, identifies a generation by PID plus start time, and must close MCP clients before stopping it. Startup only submits an async index request.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T20:58:57Z
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/cbm.py
- resource: scripts/tests/test_agent_runtime_cbm.py
- resource: https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/daemon/ipc.c
- resource: https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/daemon/bootstrap.c
- resource: https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/cli/activation_transaction.c
- resource: py_packages/agentdev_runtime/agentdev_runtime/workspace.py
- resource: .devcontainer/devcontainer.json
---

# CBM daemon lifecycle

## Rendezvous is per account, not per cache

Every CBM process — daemon, MCP client, CLI, installer — meets at
`<parent>/cbm-daemon-<euid>/`, where `<parent>` is `CBM_RUNTIME_DIR` or `/tmp`.
`HOME` and `CBM_CACHE_DIR` do not move it. Two consequences:

- Isolating a test or a second runtime from a live daemon takes a different UID
  or a different `CBM_RUNTIME_DIR`. A different cache alone isolates nothing:
  while the account's daemon serves one cache, CBM refuses to start a client
  that names another, so every client on the account shares one `CBM_CACHE_DIR`.
- Peers are authenticated by UID, so another account can neither see nor stop
  the daemon.

The UI listener port is a per-cache setting (`config set ui_enabled false` or
`--port`); it is not part of the rendezvous.

## The cache stays off the checkout

CBM refuses a cache directory with an ancestor that is owned by neither root nor
the effective UID, or that is world-writable. A bind-mounted checkout is owned
by the host's user, and the supervisor starts CBM at boot, before any lifecycle
hook could change that owner. The Dev Container therefore keeps `CBM_CACHE_DIR`
at `/root/.cache/codebase-memory-mcp`, on its own per-worktree `agentdev-cbm`
volume, never below the workspace (see [Bug: CBM cache under a checkout another
UID owns](../bugs/cbm-cache-under-foreign-owned-checkout.md)).

## Supervising it

[`agentdev-runtime cbm`](../../../../py_packages/agentdev_runtime/agentdev_runtime/cbm.py)
is the only supported control surface for supervisors. It uses
`daemon start|status|stop` and never the internal `--cbm-daemon-internal` entry
point.

- `daemon start` returns after detaching; readiness is `daemon status` exiting
  `0` with `active`. A dead daemon reports `not running` (exit `1`); a hung
  endpoint holder reports `not responding`.
- A generation is the reported PID plus its `/proc` start time. Only a matching
  generation is ever signalled, so a recycled PID is never killed.
- An MCP client that finds no daemon starts a *session-managed* one that exits
  with its last client. `daemon start` adopts it but cannot promote it to
  permanent, so the runtime starts its permanent daemon before any client.
- When a permanent daemon dies, its attached stdio clients exit too; the client
  application has to reconnect after the daemon is restarted.
- `daemon stop` refuses while committed clients remain. Shutdown therefore stops
  client applications first, then CBM, and bounds the wait before signalling the
  tracked generation.

## Installing for a non-root user

`codebase-memory-mcp install` refuses to stage from a directory the caller does
not own (`install_dir_not_owned_by_you`), including the root-owned image path.
The runtime copies the image's pinned binary byte-for-byte into the user-owned
`~/.local/bin` and runs `install` from there. That keeps the version and build
fixed and needs no network.

## Indexing at startup

Startup never waits for an index. Every startup path, the devcontainer hooks and
the standalone runtime alike, runs
[`agentdev-runtime cbm index`](../../../../py_packages/agentdev_runtime/agentdev_runtime/cbm.py),
which sends `cli --json index_repository --async true` for the workspace and
returns once CBM accepts the job: `queued`, `running`, or joined to one already
in flight. The daemon then indexes in the background.

An async job needs a daemon that outlives the request. Without one, the CLI's
temporary daemon would cancel the job when the command exits, so CBM refuses it
with an MCP error. The request therefore follows `daemon start`, and the
standalone index one-shot depends on the supervised CBM daemon.
