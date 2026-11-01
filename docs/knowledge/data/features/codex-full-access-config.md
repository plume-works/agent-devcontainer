---
type: feature
stage: deprecated
status: deprecated
description: Codex CLI sessions in the devcontainer run with full sandbox access and no approval prompts, written into Codex's config.toml on every container start without disturbing other tools' sections.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T23:20:47Z
sources:
- resource: docs/knowledge/data/plans/20261005-codex-full-access-config.md
- resource: .devcontainer/scripts/configure-codex.py
---

# Codex full-access config

Deprecated: superseded by [Claude Code and OpenCode are the only supported
harnesses](claude-and-opencode-only-harnesses.md). The runtime no longer
configures Codex; this page records the behavior it had.

## Purpose

The container is the isolation boundary, so Codex inside it should not stop for
its own sandbox and approval prompts.

## Behaviour

**On every container start**, `.devcontainer/scripts/configure-codex.py` sets
`sandbox_mode = "danger-full-access"` and `approval_policy = "never"` in
`${CODEX_HOME:-~/.codex}/config.toml`, writing it atomically at mode `0600`.

**Other tools' sections survive.** The script round-trips the file with
`tomlkit`, so comments — including codebase-memory-mcp's section markers — are
kept. `tomlkit` is declared inline in the script, so it runs in a consumer
repository whatever its `pyproject.toml` holds.

The contract is Devcontainer Codex policy.

## Edge cases

- **`config.toml` does not parse.** The step fails loudly instead of overwriting
  it.
- **The step fails.** It runs last in `postStartCommand`, so the firewall,
  keyring, and Xpra have already started.

## Open questions

None — the design is settled.

## References

- Plan: [Codex full-access
  config](../plans/20261005-codex-full-access-config.md)
