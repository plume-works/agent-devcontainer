---
type: architecture
description: The codebase-memory-mcp daemon is one per account per rendezvous directory; a supervisor drives it only through daemon start/status/stop, identifies a generation by PID plus start time, and must close MCP clients before stopping it.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-17T22:30:00Z
sources:
- resource: .devcontainer/scripts/runtime-cbm.sh
- resource: scripts/tests/test_agent_runtime_cbm.py
- resource: https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/daemon/ipc.c
- resource: https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/daemon/bootstrap.c
- resource: https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/cli/activation_transaction.c
---

# CBM daemon lifecycle

## Rendezvous is per account, not per cache

Every CBM process — daemon, MCP client, CLI, installer — meets at
`<parent>/cbm-daemon-<euid>/`, where `<parent>` is `CBM_RUNTIME_DIR` or `/tmp`.
`HOME` and `CBM_CACHE_DIR` do not move it. Two consequences:

- Isolating a test or a second runtime from a live daemon takes a different UID
  or a different `CBM_RUNTIME_DIR`; a different cache alone attaches to the live
  daemon and could stop it.
- Peers are authenticated by UID, so another account can neither see nor stop
  the daemon.

The UI listener port is a per-cache setting (`config set ui_enabled false` or
`--port`); it is not part of the rendezvous.

## Supervising it

[runtime-cbm.sh](../../../../.devcontainer/scripts/runtime-cbm.sh) is the only
supported control surface for supervisors. It uses `daemon start|status|stop`
and never the internal `--cbm-daemon-internal` entry point.

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
