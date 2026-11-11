---
type: bug
stage: done
severity: high
description: Claude's saved state stops reaching the persistent volume once ~/.claude.json is replaced by a regular file, so trust, MCP, and session state written after that point are lost when the container is recreated.
sources:
- resource: .devcontainer/scripts/postCreateCommand.sh
- resource: .devcontainer/scripts/codebase-memory-mcp-install.sh
- resource: docs/knowledge/data/spec/catalog-lifecycle.md
---

# Bug: ~/.claude.json stops being the volume symlink

## Symptom

[catalog-lifecycle](../spec/catalog-lifecycle.md) requires `/root/.claude.json`
to be a symlink to `/root/.claude/claude.json` in the persistent `~/.claude`
volume. In a running devcontainer, `/root/.claude.json` is a regular `0600`
file, and the volume copy stopped changing hours before the live file did. Any
state Claude writes after the link is replaced — workspace trust, MCP choices,
Remote Control state, project history — lives only in the container layer and is
lost when the container is recreated.

## Reproduction

In a container that has run an interactive Claude session after post-create:

``` bash
test -L /root/.claude.json && echo symlink || echo regular-file
stat -c '%y %a %n' /root/.claude.json /root/.claude/claude.json
```

Expected: `symlink`, with both paths showing the same file. Observed:
`regular-file`, with the live file newer than the volume copy and its backups
accumulating under `/root/.claude/backups/`.

## Root cause

Not confirmed. Eliminated: `codebase-memory-mcp-install.sh` materializes the
link during its install but restores it on every exit path through an `EXIT`
trap, and no other repository script writes the path. Leading hypothesis: Claude
Code saves its global config by writing a temporary file and renaming it over
`~/.claude.json`, which replaces the symlink instead of writing through it.
Confirming it takes one check: recreate the link, start a Claude session, and
test the path again after its first config save.

## Potential solution

Candidate: set `CLAUDE_CONFIG_DIR=/root/.claude` in the container environment so
Claude keeps its global config inside the volume directory itself and no symlink
is needed. The candidate stands or falls on whether Claude reads
`$CLAUDE_CONFIG_DIR/.claude.json` in place of `~/.claude.json`, and on migrating
the existing `claude.json` in the volume to that name.
`preapprove-claude-workspace.sh` and `codebase-memory-mcp-install.sh` would then
target the same path.

## Fix

Shipped by [Run the Dev Container as a non-root account with one home
volume](../plans/20261030-devcontainer-home-volume.md). The Dev Container's
whole home is one per-instance volume, so `~/.claude.json` is an ordinary file
on that volume and no symlink is needed: however Claude rewrites the file, the
result stays on the volume. `agentdev-runtime state create` no longer links the
file, and a home that still holds the link to `~/.claude/claude.json` has it
replaced by a regular file with the target's content before the
codebase-memory-mcp cleanup runs (`agent_state.py::unlink_claude_json`).

## Key references

- `py_packages/agentdev_runtime/agentdev_runtime/agent_state.py::unlink_claude_json`
  — replaces the link with the file it points to
- `.devcontainer/scripts/codebase-memory-mcp-install.sh` —
  `restore_claude_json_symlink`
- `py_packages/agentdev_runtime/agentdev_runtime/claude_state.py::preapprove` —
  the state file, written through the link at post-create
