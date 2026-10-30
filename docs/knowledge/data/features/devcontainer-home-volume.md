---
type: feature
stage: accepted
description: The Dev Container runs as a non-root account matched to the host user, with its whole home on one per-instance volume, replacing the per-directory state volumes under /root and the ~/.claude.json symlink.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T06:05:00Z
sources:
- resource: docs/knowledge/data/architecture/devcontainer-home-volume.md
- resource: .devcontainer/devcontainer.json
- resource: .devcontainer/docker-compose.yml
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: compose.opencode.yml
---

# Dev Container home volume

## Purpose

Every piece of per-instance state in the Dev Container needs its own volume
today, because `/root` lives on the container filesystem: agent configuration,
OpenCode's database, and the CBM and pre-commit caches each have one, and
`~/.claude.json` needs a symlink into the `~/.claude` volume. The deploy runtime
needs none of that: its account's whole home is one volume. This feature gives
the Dev Container the same model (see [Dev Container home
volume](../architecture/devcontainer-home-volume.md)).

## Behaviour

**A non-root account.** The image provides an account `agent` with no home
directory, and the Dev Container's `remoteUser` is `agent`. On a Linux host the
devcontainer CLI remaps its UID and GID to the host user's, so a bind-mounted
checkout is writable without changing its owner. The supervisor stays root; user
services, lifecycle commands, and editor sessions run as `agent`, with
passwordless `sudo`.

**One home volume.** `/home/agent` is one per-instance volume that starts empty
and is claimed by the account on first start. Agent configuration and sessions,
`~/.claude.json`, OpenCode's database, and the CBM and pre-commit caches live on
it at their default paths. The per-directory volumes and the `~/.claude.json`
symlink are gone.

**Shared credentials per UID cohort.** Claude and Codex credentials stay on a
volume shared by every Dev Container instance, mounted where the deploy runtime
mounts it, and named after the host user's UID and GID. Containers with
different IDs never share one.

**Shell setup outside the home.** The shell configuration the image gives the
account today through `/root/.bashrc` (the `~/.local/bin` path, the repository's
`docker/bin` wrapper, `bun`, history settings) comes from system-wide files, so
an empty home has it and an image upgrade updates it.

## Edge cases

- **An existing Dev Container is rebuilt onto this version.** Its old volumes
  are no longer mounted; agent configuration, sessions, OpenCode logins, and
  caches start empty, and every agent logs in once. The state is not migrated
  (owner decision).
- **A deploy instance is upgraded.** The deploy runtime keeps uv's cache, Python
  installs, and project venv on its home volume too; its old `/uv` volume is no
  longer mounted, and the uv state is rebuilt once.
- **Editor servers.** `~/.vscode-server` and the other editors' servers now
  persist across rebuilds with every version they install. Nothing cleans them;
  the risk is accepted (owner decision).
- **A host without UID remapping** (macOS, Windows). The account keeps its image
  UID and GID, and the checkout must be writable by them, as Docker Desktop's
  file sharing provides.
- **A host checkout another UID owns.** The bootstrap refuses to start and names
  the UID the checkout must be writable by, as the deploy runtime does.

## Open questions

None — every design question this feature raised is settled.
