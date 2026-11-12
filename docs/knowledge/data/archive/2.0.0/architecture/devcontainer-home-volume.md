---
type: architecture
description: The Dev Container runs as a non-root account remapped to the host user, whose whole home is one per-instance volume, like the deploy runtime, in place of per-directory state volumes under /root; editor servers persisting on that volume are an accepted risk.
sources:
- resource: .devcontainer/devcontainer.json
- resource: compose.opencode.yml
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: docker/base/agentdev-base.Dockerfile
- resource: py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: .devcontainer/devcontainer-init.sh
- resource: scripts/run-root-tests
- resource: scripts/tests/conftest.py
---

# Dev Container home volume

## Decision

The Dev Container adopts the deploy runtime's account model (see [Standalone
OpenCode runtime](standalone-opencode-runtime.md)): a non-root runtime account
whose home starts empty and is one per-instance volume. Per-instance state —
agent configuration and sessions, `~/.claude.json`, OpenCode's database, and the
pre-commit cache — lives on that volume. Only Claude credentials stay on the
shared auth volume.

The decision was made by the repository owner. Per-directory state from before
the change is dropped, not migrated, and Claude logs in once on the new auth
volume.

## The account and its volumes

- **The account.** `agentdev-devcontainer` defines `agent` (1000:1000) with an
  empty `/home/agent` it owns. Its metadata sets `remoteUser: agent` and
  `updateRemoteUserUID: true`, so on Linux the devcontainer CLI remaps the
  account to the UID and GID of the host user running it. The container's own
  user stays root: PID 1 is the supervisor, which runs every user service as
  `agent`.
- **The home volume.** The image metadata mounts
  `agentdev-home-${devcontainerId}` at `/home/agent`. Agent configuration and
  sessions, `~/.claude.json` (a regular file), OpenCode's database, uv's cache
  and interpreters, each checkout's environment under `AGENTDEV_VENV_ROOT`
  (`~/.local/share/uv/venvs`), and the pre-commit cache all live there at their
  default paths.
- **The auth volume.** Claude's credentials live on
  `agentdev-agents-auth-<uid>-<gid>` at `/var/lib/agentdev/auth`, which
  `devcontainer-init.sh` names after the host user's IDs; see [Agent auth
  persistence](../../1.0.0/architecture/agent-auth-persistence.md).
- **The bootstrap.** For a non-root account it claims an empty home mount root,
  writes the sudoers entry, initializes the auth volume under its lock, and
  refuses a checkout the account cannot write, naming the UID it needs. A root
  account keeps the root path, with no claim and no sudoers entry.
- **The sibling checkout.** The create phase re-owns `/workspaces/project` once
  when it is a mount another UID owns, unless it is the open workspace.
- **Shell setup.** The base image writes its `PATH` and history blocks into
  `/etc/bash.bashrc` and `/etc/fish/conf.d/`, so an empty home gets them.

## Constraints

- The image must ship `/home/agent` as an empty directory: the devcontainer
  CLI's UID update re-owns the account's home recursively and fails the build
  when it is missing. Docker copies the empty directory's ownership to a fresh
  volume, so the volume starts empty and owned by the remapped account.
- The home must start empty. The deploy image creates no home and keeps
  build-time tools out of it. Anything the base image builds into a home would
  be copied into the volume once and then never updated by an image upgrade.
- The runtime account is not root. A host checkout must be writable by its
  UID/GID, the same requirement the deploy runtime's bootstrap enforces.
- Root hosts are unsupported, by the repository owner's decision. When the host
  user is root, the devcontainer CLI does not remap `agent`, which keeps
  1000:1000, and the bootstrap refuses a root-owned checkout with an error
  naming the UID it needs. Cloud sessions run on a host toolchain and never
  start the Dev Container.

## Tests that need root

Some tests need root itself, not just the runtime account: supervisord can
switch a program to `AGENTDEV_USER` only as root, and the bootstrap tests
`chown` scratch files to other UIDs. They carry the `requires_root` marker and
skip in a run that is not root, so the suite passes as `agent`.

`scripts/run-root-tests` runs them as root from the runtime account, through the
passwordless `sudo` the bootstrap grants:

- It refuses to start as root.
- It runs the project environment's own Python through `sudo env -i`, never `uv`
  and never `sudo -E`. Root therefore never syncs or writes into `.venv`, and
  only the variables it names reach root. `env -i` sets the list because
  `sudo`'s `secure_path` would replace `PATH`. No token is on the list.
- It turns off bytecode and the pytest cache, and gives root its own scratch
  root under `/tmp`, so no file root leaves blocks a later run as `agent`.

Under the launcher, a root run that selects any test without the marker is
refused. The guard catches mistakes and is not a security boundary. A root run
without the launcher stays unrestricted, because cloud session hosts, GitHub
`container:` jobs and a root Dev Container run the whole suite as root on
purpose. CI's Dev Container image job runs the suite as `agent`, then the
launcher, and fails if that run left a root-owned file in the checkout or in the
`agent` scratch root.

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
  at image build time with an empty home directory, which that update re-owns.
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
