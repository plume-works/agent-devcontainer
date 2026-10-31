---
type: architecture
description: The Dev Container is to run as a non-root account whose whole home is one per-instance volume, like the deploy runtime, replacing the per-directory state volumes under /root; editor servers persisting on that volume are an accepted risk.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T04:32:14Z
sources:
- resource: .devcontainer/devcontainer.json
- resource: compose.opencode.yml
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: docker/base/agentdev-base.Dockerfile
- resource: py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
---

# Dev Container home volume

## Decision

The Dev Container adopts the deploy runtime's account model (see [Standalone
OpenCode runtime](standalone-opencode-runtime.md)): a non-root runtime account
whose home starts empty and is one per-instance volume. Per-instance state —
agent configuration and sessions, `~/.claude.json`, OpenCode's database, and the
CBM and pre-commit caches — lives on that volume. Only Claude and Codex
credentials stay on the shared auth volume.

The decision was made by the repository owner. Existing instances' per-directory
state is dropped, not migrated; shared credentials are unaffected.

## What it replaces

The Dev Container runs as root with `/root` on the container filesystem, so each
piece of state needs its own volume: `agentdev-claude`, `agentdev-codex`,
`agentdev-opencode`, `agentdev-uv`, and the volumes holding the CBM and
pre-commit caches. A volume cannot be mounted on a single file, so
`~/.claude.json` is kept inside the `~/.claude` volume and symlinked, and the
CBM install has to work around that symlink (see [Agent auth
persistence](agent-auth-persistence.md)). With the whole home on one volume, the
file is an ordinary file and the per-directory mounts go away.

## Constraints

- The home must start empty. The deploy image creates no home and keeps
  build-time tools out of it (`gh-stack` is installed under
  `/usr/local/lib/agentdev`). Anything the base image builds into a home would
  be copied into the volume once and then never updated by an image upgrade.
- The runtime account is not root. A host checkout must be writable by its
  UID/GID, the same requirement the deploy runtime's bootstrap enforces.

## Rejected alternatives

- **A volume on `/root`, still running as root.** The base image builds shell
  configuration, `gh` extensions, and tool state into `/root`. A volume there
  freezes all of it at the first create's image unless every such file first
  moves to an image path.
- **A volume on `/root` refreshed from the image on every start.** Overwrites
  the user's own edits to those files and needs an ownership decision for each
  one.
- **Creating the account at container start, as deploy does.** The devcontainer
  CLI's UID update needs an account the image defines, so the account is created
  at image build time without a home directory.
- **A separate `/uv` volume, in either runtime.** The owner chose one home
  volume; uv's cache, Python installs, and project venv live on it.
- **Keeping per-directory volumes.** Every new piece of state needs its own
  volume decision, and single files such as `~/.claude.json` need symlink
  workarounds.

## Accepted risk: editor servers on the home volume

VS Code and its derivatives install their remote servers in the home
(`~/.vscode-server`, `~/.vscode-insiders-server`, `~/.cursor-server`,
`~/.windsurf-server`, `~/.vscodium-server`). Today a rebuild discards them; on a
home volume they persist across rebuilds, with every server version and
extension an editor update installed. Nothing in the runtime removes them, and
whether each editor prunes its own old versions is unverified. The risk is
unbounded growth of the home volume, and a broken server install surviving the
rebuild that would otherwise reset it.

The repository owner accepted the risk: editor servers stay on the home volume
with no cleanup. Keeping them off the volume, and pruning old server versions at
create, were both declined.
