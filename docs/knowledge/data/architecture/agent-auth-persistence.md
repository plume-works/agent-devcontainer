---
type: architecture
description: Claude Code credentials live on one Docker volume named after the host user's UID and GID and shared by every Dev Container of that user, while OpenCode's logins, ~/.claude.json, and the rest of each agent's state live on each instance's home volume.
sources:
- resource: .devcontainer/docker-compose.yml
- resource: .devcontainer/devcontainer.json
- resource: .devcontainer/devcontainer-init.sh
- resource: py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
- resource: https://opencode.ai/v2/docs
- resource: https://github.com/Dr-QP/Dr.QP/pull/417
- resource: https://github.com/Dr-QP/Dr.QP/pull/436
- resource: https://github.com/Dr-QP/Dr.QP/pull/438
- resource: https://github.com/anthropics/claude-code/issues/21765
---

# Agent auth persistence

## Decision

Agent state is split in two:

- **Claude Code credentials are shared per host user.** One volume,
  `agentdev-agents-auth-<uid>-<gid>`, named after the host user's UID and GID,
  is declared with an explicit top-level `name:` and mounted at
  `/var/lib/agentdev/auth`. The image points Claude Code's credential store at
  `/var/lib/agentdev/auth/claude` through `CLAUDE_SECURESTORAGE_CONFIG_DIR`.
- **Everything else is per instance**, on the home volume the image mounts at
  `/home/agent` (see [Dev Container home volume](devcontainer-home-volume.md)),
  so a worktree, a clone, and a Codespace each get their own.
- **OpenCode's logins are per instance.** OpenCode v2 keeps provider logins in
  the SQLite database in its data directory, on the home volume, and never
  writes `auth.json`. There is no file to share, so each worktree logs in once
  and keeps that login across rebuilds. The maintainer accepted losing
  cross-worktree OpenCode login sharing.

`~/.claude.json` is a regular file on the home volume. A home that still holds
the former link to `~/.claude/claude.json` has it replaced by the file it
pointed to.

## Why the credential volume is pinned to a literal name

Compose prefixes a volume name with its project name unless the volume declares
`name:` explicitly. That prefix is exactly what isolates one devcontainer
instance from another. For credentials the isolation is the defect, not the
feature: a second worktree would demand a fresh browser login for each agent.
Pinning the literal name is what makes one login serve every instance.

## Why the name carries the host user's IDs

The runtime account is remapped to the host user's UID and GID, and the
bootstrap refuses an auth volume another UID owns. Naming the volume after the
IDs keeps two host users on one engine from sharing, or locking each other out
of, one credential store.

## Why the rest of the state is not shared

The remainder of each agent's state records **absolute workspace paths**.
Sharing it across instances would point one worktree's history and session state
at another worktree's directories.

## Consequences

- A rebuild never requires re-authenticating any agent. A new worktree needs a
  fresh OpenCode login.
- Adding a new agent means deciding which half of the split its state belongs
  to; credentials go in the shared volume, path-bearing state does not.
- The volume is declared `external: true`, so it must exist before Compose
  starts; `devcontainer-init.sh` creates it on the host and writes its name to
  `.devcontainer/.env` as `AGENTDEV_AUTH_VOLUME`.
- Worktrees on one host share a single Claude credential file, so each sees the
  others' token refreshes. Claude.ai refresh tokens are single-use
  ([anthropics/claude-code#21765](https://github.com/anthropics/claude-code/issues/21765)),
  so two Claude processes refreshing at the same moment can race, and the loser
  reaches `Login expired`. This is a known limitation; a fresh `/login` in any
  container recovers every instance.
