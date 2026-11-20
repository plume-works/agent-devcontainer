---
type: adr
stage: accepted
description: Containers share only the Claude credentials, on one auth volume for each UID/GID pair. All other agent state stays on the home volume of each instance.
---

# Containers share only the Claude credentials, on one auth volume for each UID/GID pair

The auth volume holds only the Claude credentials. In the Dev Container, its
name `agentdev-agents-auth-<uid>-<gid>` contains the IDs of the user. As a
result, one login serves each container of that user, and two users on one
engine neither share nor lock each other out of one credential store. All other
agent state stays on the home volume of the instance, because it records
absolute workspace paths and holds the data of one project.

## Considered Options

- Share all of a home or agent directory. Rejected: the sessions of one worktree
  then point to the directories of another worktree. Also, sessions,
  configuration, keyrings, and caches record per-project state, and two
  containers that write them would corrupt each other.
- Share across UID/GID pairs. Rejected: a container would then have to rewrite
  the file ownership of another running container.
- A credential volume with the Compose prefix. Rejected: each new worktree then
  needs a new login for each agent.
- Copy, renew, or send credentials to other instances. Rejected: claude.ai
  rotates the refresh token at each renewal, so a copy stays valid only in the
  first instance that renews it, and the rest reach `Login expired`.
- Share the OpenCode data directory or its `auth.json`. Rejected: the directory
  holds a WAL-mode SQLite database with the sessions, and concurrent containers
  that write one copy damage it. OpenCode v2 keeps logins in its database and
  writes no `auth.json`.

## Consequences

- A new agent needs a decision about each part of its state: credentials can go
  on the auth volume, and state that holds paths cannot.
- Each worktree needs its own OpenCode login. The maintainer accepted this.
- claude.ai refresh tokens are single-use, so two instances that renew the token
  at the same time can leave one at `Login expired`. A new `/login` in any
  container recovers all instances. The maintainer accepted this.
