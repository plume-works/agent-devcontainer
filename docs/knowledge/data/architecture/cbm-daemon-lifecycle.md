---
type: architecture
description: The codebase-memory-mcp daemon is one per account per rendezvous directory; a supervisor drives it only through daemon start/status/stop, identifies a generation by PID plus start time, and must close MCP clients before stopping it. Startup only submits an async index request, and cbm's Codex hooks live in hooks.json.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T12:00:00Z
sources:
- resource: .devcontainer/scripts/runtime-cbm.sh
- resource: scripts/tests/test_agent_runtime_cbm.py
- resource: https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/daemon/ipc.c
- resource: https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/daemon/bootstrap.c
- resource: https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/cli/activation_transaction.c
- resource: .devcontainer/scripts/codebase-memory-mcp-index.sh
- resource: .devcontainer/scripts/codebase-memory-mcp-install.sh
- resource: .devcontainer/scripts/repair-codex-cbm-hooks-block.py
- resource: .devcontainer/scripts/runtime-workspace.sh
- resource: .devcontainer/devcontainer.json
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

## The cache stays off the checkout

CBM refuses a cache directory with an ancestor that is owned by neither root nor
the effective UID, or that is world-writable. A bind-mounted checkout is owned
by the host's user, and the supervisor starts CBM at boot, before any lifecycle
hook could change that owner. The Dev Container therefore keeps `CBM_CACHE_DIR`
at `/root/.cache/codebase-memory-mcp`, on its own per-worktree `agentdev-cbm`
volume, never below the workspace (see [Bug: CBM cache under a checkout another
UID owns](../bugs/cbm-cache-under-foreign-owned-checkout.md)).

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

## Indexing at startup

Startup never waits for an index. Every startup path, the devcontainer hooks and
the standalone runtime alike, runs
[codebase-memory-mcp-index.sh](../../../../.devcontainer/scripts/codebase-memory-mcp-index.sh),
which sends `cli --json index_repository --async true` for the workspace and
returns once CBM accepts the job: `queued`, `running`, or joined to one already
in flight. The daemon then indexes in the background.

An async job needs a daemon that outlives the request. Without one, the CLI's
temporary daemon would cancel the job when the command exits, so CBM refuses it
with an MCP error. The request therefore follows `daemon start`, and the
standalone index one-shot depends on the supervised CBM daemon.

## Codex hooks live in hooks.json

cbm writes its Codex `SessionStart` and `SubagentStart` hooks to
`$CODEX_HOME/hooks.json` when that file exists, and otherwise to a marked block
at the end of `config.toml`. Codex rewrites `config.toml` and inserts its own
tables above a trailing comment marker, which breaks the block apart (see [Bug:
Codex tables inside cbm's hooks
block](../bugs/cbm-codex-hooks-block-foreign-tables.md)). The install therefore
creates `hooks.json` as `{}` when absent, so the hooks have one representation
outside the file Codex rewrites. Given `hooks.json`, cbm migrates a well-formed
TOML block out of `config.toml` itself.

An orphaned block, a marker without its partner, is removed before the install
only when every hook table it claims is exactly cbm's canonical content invoking
the installed binary. It claims the contiguous run of hook tables after a lone
opening marker, or the last run before a lone closing one; hook tables elsewhere
are the user's and stay. A modified or foreign table in that run leaves the file
unchanged and fails the install, naming the table. Comments are kept.

The MCP block keeps its trailing marker, so Codex tables registered after cbm
installs land above that marker, and the next install moves it. The standalone
configuration step therefore registers the catalog before installing cbm, which
leaves both files byte-identical across restarts.
