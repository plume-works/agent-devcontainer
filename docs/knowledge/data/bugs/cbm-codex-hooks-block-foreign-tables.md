---
type: bug
description: Tables Codex writes into config.toml land inside codebase-memory-mcp's trailing SessionStart block, so every later cbm install refuses with ambiguous_hook_ownership, and the failed install used to abort postCreate and skip all of postStart.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-09T23:20:00Z
sources:
- resource: https://github.com/DeusData/codebase-memory-mcp/issues/2435
  title: 'install: tables Codex Desktop appends above the trailing SessionStart closing marker make the Codex hook preflight refuse (`ambiguous_hook_ownership`)'
- resource: https://github.com/DeusData/codebase-memory-mcp/issues/2228
  title: install deletes foreign tables placed between the managed MCP markers in ~/.codex/config.toml
- resource: .devcontainer/scripts/codebase-memory-mcp-install.sh
- resource: .devcontainer/scripts/repair-codex-cbm-hooks-block.py
- resource: .devcontainer/scripts/postCreateCommand.sh
- resource: .devcontainer/scripts/postStartCommand.sh
---

# Bug: Codex tables inside cbm's hooks block break cbm install

## Symptom

`codebase-memory-mcp install -y --force` fails during postCreate with:

``` text
error: agent_config agent=Codex CLI op=hook_preflight path=/root/.codex/config.toml reason=ambiguous_hook_ownership
```

and `logs/activation-events.ndjson` under `$CBM_CACHE_DIR` records
`phase: failed` with "agent configuration refresh or cleanup incomplete".
Because `postCreateCommand.sh` runs under `set -e`, the failure ended the
lifecycle: postStart never ran, so the cbm daemon was not started, and the
firewall, keyring, Xpra, git `safe.directory`, and Remote Control were missing
too. The daemon only came up later, started on demand by an agent's MCP client.

`~/.codex` is a persistent volume, so once the file is in this state every
container create fails the same way until the file is repaired.

## Reproduction

In a throwaway `CODEX_HOME`, with no real config touched:

``` bash
printf 'model = "x"\n' > "$CODEX_HOME/config.toml"
codebase-memory-mcp install -y --force          # passes; marker is the last line
codex plugin marketplace add /workspaces/agent-devcontainer
tail -4 "$CODEX_HOME/config.toml"                # [marketplaces.*] sits above the marker
codebase-memory-mcp install -y --force          # exit 1, ambiguous_hook_ownership
```

Upstream issue #2435 has the same reproduction with a hand-inserted table.

## Root cause

When Codex hooks live in `config.toml`, cbm appends its
`# >>> codebase-memory-mcp SessionStart >>>` … `# <<< … <<<` block at the end of
the file, so the closing marker is the last line. Codex treats a trailing
comment as document decoration and inserts every new table above it — any Codex
write does this, including `codex plugin marketplace add`/`plugin add` from
`reinstall-agentdev-codex.sh`, hook trust (`[hooks.state]`), project trust, and
TUI notices. cbm's hooks preflight then no longer sees exactly its own tables
between the markers and refuses the whole Codex step, fail-closed. Even a blank
line before the closing marker is enough to trigger the refusal.

The postCreate order guarantees recurrence: the cbm install runs first and the
Codex plugin reinstall runs after it, in postCreate and again in postAttach.

Upstream:
[DeusData/codebase-memory-mcp#2435](https://github.com/DeusData/codebase-memory-mcp/issues/2435),
open as of 0.11.0.

## Fix

- `repair-codex-cbm-hooks-block.py` runs right before the installer in
  `codebase-memory-mcp-install.sh`. It keeps the `[[hooks.SessionStart]]` and
  `[[hooks.SubagentStart]]` tables (and their `.hooks` arrays) inside the block,
  moves everything from the first other table header — with the comments
  directly above it — to just below the closing marker, and drops blank lines
  before the marker. The parsed TOML is unchanged. A config with no block, an
  unterminated block, or a block that is already clean is left byte-identical.
- `postCreateCommand.sh` treats a failed cbm install as a warning, so it no
  longer skips postStart.

The repair can be dropped once a cbm release fixes #2435.

The MCP block is deliberately left alone. Codex also writes
`[mcp_servers.codebase-memory-mcp.tools.*]` approval tables into it; cbm 0.11.0
deletes them on install (upstream #2228), and moving them below the MCP block
does not help, because the installer then refuses with `op=mcp_install`.

## Key references

Verified anchor points (line numbers as of 2026-10-09):

- `.devcontainer/scripts/repair-codex-cbm-hooks-block.py:47` — `repair`
- `.devcontainer/scripts/repair-codex-cbm-hooks-block.py:18` — `OWNED_HEADER`,
  the tables cbm owns inside the block
- `.devcontainer/scripts/codebase-memory-mcp-install.sh:79` — repair call ahead
  of the installer
- `.devcontainer/scripts/codebase-memory-mcp-install.sh:82` —
  `codebase-memory-mcp install -y --force`
- `.devcontainer/scripts/postCreateCommand.sh:67` — non-fatal cbm install call
- `.devcontainer/scripts/postCreateCommand.sh:94` —
  `reinstall-agentdev-codex.sh`, a Codex config write after the install
- `.devcontainer/scripts/postAttachCommand.sh:14` —
  `reinstall-agentdev-codex.sh` again
- `.devcontainer/scripts/postStartCommand.sh:9` —
  `codebase-memory-mcp-start.sh`, skipped whenever postCreate fails
- `scripts/tests/test_repair_codex_cbm_hooks_block.py` — repair behavior
