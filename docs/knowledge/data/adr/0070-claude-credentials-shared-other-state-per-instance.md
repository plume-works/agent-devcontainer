---
type: adr
stage: accepted
description: Containers share only the Claude credentials, on one auth volume for each UID/GID pair, and all other agent state stays on the home volume of each instance.
---

# Containers share only the Claude credentials, on one auth volume for each UID/GID pair

The auth volume holds only the Claude credentials. In the Dev Container, its
name `agentdev-agents-auth-<uid>-<gid>` contains the IDs of the user. As a
result, one login serves each container of that user, and two users on one
engine stay apart. All other agent state stays on the home volume of the
instance, because it records absolute workspace paths and holds the data of one
project.

## Considered Options

- Share all of a home or agent directory. Rejected: the sessions of one worktree
  then point to the directories of another worktree. Also, two containers that
  write the same caches and keyrings cause damage to the data of the other.
- Share across UID/GID pairs. Rejected: a container must then change the file
  owners of a different container that runs.
- A credential volume with the Compose prefix. Rejected: each new worktree then
  needs a new login for each agent.
- Copy, refresh, or send credentials to other workspaces. Rejected: claude.ai
  changes the refresh token at each refresh, so a copy stays valid only in the
  first workspace that refreshes.
- Share the OpenCode data directory or its `auth.json`. Rejected: the directory
  holds a WAL-mode SQLite database with the sessions, and concurrent containers
  that write one copy damage it. OpenCode v2 keeps logins in its database and
  writes no `auth.json`.

## Consequences

- The auth volume is at `/var/lib/agentdev/auth`, and the image sets
  `CLAUDE_SECURESTORAGE_CONFIG_DIR` to `/var/lib/agentdev/auth/claude`.
- The volume has an explicit `name:`, because Compose otherwise adds the project
  name, which isolates each instance. It is `external: true`, so it must exist
  before Compose starts. `.devcontainer/devcontainer-init.sh` creates it on the
  host and writes its name to `.devcontainer/.env` as `AGENTDEV_AUTH_VOLUME`.
- The bootstrap refuses an auth volume that has an entry of a different UID.
- `~/.claude.json` is a regular file on the home volume. The runtime replaces an
  old link to `~/.claude/claude.json` with the file that it points to.
- A new agent needs a decision about each part of its state: credentials can go
  on the auth volume, and state that holds paths cannot.
- The deploy bootstrap creates the runtime account at each start, because a new
  container has no account and its user and group IDs are deployment settings.
- `~/.local/share/opencode` stays at its default path on the home volume, with
  no volume of its own, so its logins and sessions stay after a rebuild.
- Each worktree needs its own OpenCode login. The maintainer accepted this.
- claude.ai refresh tokens are single-use, so two instances that refresh at the
  same time can leave one at `Login expired`. A new `/login` in any container
  recovers all instances. The maintainer accepted this.
