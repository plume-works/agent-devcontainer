---
type: architecture
description: Agent credentials live on one Docker volume pinned to a literal name and shared by every devcontainer instance, while the rest of each agent's state is mounted per instance; a directory-backed volume cannot mount at ~/.claude.json, so that file is a symlink into the volume.
generated:
  by: claude-code/opus-5
  at: 2026-09-04T00:00:00Z
sources:
- resource: .devcontainer/docker-compose.yml
- resource: .devcontainer/devcontainer.json
- resource: .devcontainer/scripts/postCreateCommand.sh
- resource: .devcontainer/scripts/link-codex-auth.sh
- resource: .devcontainer/scripts/codebase-memory-mcp-install.sh
- resource: https://github.com/Dr-QP/Dr.QP/pull/417
- resource: https://github.com/Dr-QP/Dr.QP/pull/436
- resource: https://github.com/Dr-QP/Dr.QP/pull/438
---

# Agent auth persistence

## Decision

Agent state is split in two:

- **Credentials are shared.** One volume, `agentdev-agents-auth`, is declared
  with an explicit top-level `name:` and mounted at `/root/.agents-auth`. Claude
  Code's credential store is pointed at `/root/.agents-auth/claude` through
  `CLAUDE_SECURESTORAGE_CONFIG_DIR`, and Codex's `auth.json` is symlinked to
  `/root/.agents-auth/codex/auth.json`.
- **Everything else is per instance.** The `agentdev-claude` and
  `agentdev-codex` mounts carry each agent's remaining state and are left
  Compose-project-scoped, so a worktree, a clone, and a Codespace each get their
  own.

`~/.claude.json` is a **symlink** into the shared volume, never a mount.

## Why the credential volume is pinned to a literal name

Compose prefixes a volume name with its project name unless the volume declares
`name:` explicitly. That prefix is exactly what isolates one devcontainer
instance from another. For credentials the isolation is the defect, not the
feature: a second worktree would demand a fresh browser login for both agents.
Pinning the literal name is what makes one login serve every instance.

## Why the rest of the state is not shared

The remainder of each agent's state records **absolute workspace paths**.
Sharing it across instances would point one worktree's history and session state
at another worktree's directories.

## Why `~/.claude.json` is a symlink and not a mount

Docker named volumes are always **directory**-backed. Mounting one at the
`~/.claude.json` path replaces the file Claude Code expects with an empty
directory, and the agent fails to read its own configuration. The file therefore
lives inside the volume at `/root/.claude/claude.json` and `~/.claude.json` is
symlinked to it.

The ordering this forces is load-bearing: `postCreateCommand.sh` establishes the
symlink *before* the codebase-memory-mcp install runs. That installer cannot
write through a symlink, so it materializes the target as a real file, installs,
then folds the result back and relinks under an `EXIT` trap. With the symlink
absent, the install writes outside the volume and the MCP entry does not survive
a rebuild.

A pre-existing regular file at `~/.claude.json` is discarded rather than
migrated, because its content predates the volume and would otherwise mask it.

## Consequences

- A rebuild never requires re-authenticating either agent.
- Adding a new agent means deciding which half of the split its state belongs
  to; credentials go in the shared volume, path-bearing state does not.
- The volume is declared `external: true`, so it must exist before Compose
  starts; `devcontainer-init.sh` creates it on the host.
