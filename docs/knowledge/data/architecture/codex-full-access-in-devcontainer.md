---
type: architecture
description: Why devcontainer Codex sessions run with sandbox_mode danger-full-access and approval_policy never, written into config.toml on every start by a tomlkit script that carries its own dependencies.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-08T00:00:00Z
sources:
- resource: .devcontainer/scripts/configure-codex.py
- resource: .devcontainer/scripts/postStartCommand.sh
---

# Codex full access in the devcontainer

The devcontainer is the isolation boundary, so Codex runs inside it with no
sandbox of its own and no approval prompts:
`sandbox_mode = "danger-full-access"` and `approval_policy = "never"`.
Interactive Codex CLI sessions take these from
`${CODEX_HOME:-~/.codex}/config.toml` unless a command-line flag overrides them,
and Codex does not set them itself, so the container writes them there.
`codex exec` runs pass the equivalent flag explicitly; see [Headless Codex
runs](codex-headless-runs.md).

`.devcontainer/scripts/configure-codex.py` sets both keys on every container
start, called last from `postStartCommand.sh` so that a failure cannot keep the
firewall, keyring, or Xpra from starting. Rewriting them on every start means a
session that changed either value gets it back on the next start. The Codex home
is kept at mode `0700` and the file at `0600`, replaced atomically through a
temporary file in the same directory. An unparseable `config.toml` fails the
step rather than being overwritten.

## Constraints

**Comments must survive.** `config.toml` is shared with codebase-memory-mcp,
whose installer finds its sections by the comment markers
`# >>> codebase-memory-mcp MCP >>>` and `# <<< codebase-memory-mcp MCP <<<`. The
script parses and writes with `tomlkit`, which keeps comments and formatting.

**New keys go at the top of the file.** The file can open with that marker
comment, and `tomlkit` adds a new top-level key after a leading comment block,
which puts it inside the other tool's section. Keys that already exist are
updated where they are; missing keys are written above everything else.

**The script needs nothing from the consumer project.** `.devcontainer/scripts/`
ships to template consumers, and their `pyproject.toml` is theirs to rewrite.
The script declares `tomlkit` in PEP 723 inline metadata and runs through
`uv run --script`, so the dependency travels with the script. PyPI is on the
firewall allowlist and `UV_CACHE_DIR` is on the persistent `/uv` volume.

## Rejected alternatives

- **`toml` (`python3-toml` apt or the `toml` PyPI package):** its `dump`
  discards comments, which would erase codebase-memory-mcp's section markers on
  every start.
- **`tomlkit` as a project dev dependency run through plain `uv run`:** a
  consumer whose `pyproject.toml` lacks it fails at container start.
- **A shell or awk line edit:** not a TOML parser.
- **`codex --dangerously-bypass-approvals-and-sandbox` or an alias:** applies
  per invocation, not as a property of the container.
