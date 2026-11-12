---
type: spec
description: Where the Dev Container keeps state — Claude credentials on an auth volume the host init creates per host UID and GID, everything else on a per-instance home volume that starts empty and the bootstrap claims for the remapped account, each checkout's .venv linked to its own environment on that volume, and root-only tests run through a launcher.
sources:
- resource: .devcontainer/devcontainer-init.sh
- resource: .devcontainer/docker-compose.yml
- resource: .devcontainer/devcontainer.json
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: docker/base/agentdev-base.Dockerfile
- resource: py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/project.py
- resource: .pre-commit-config.yaml
- resource: scripts/run-root-tests
- resource: scripts/tests/conftest.py
- resource: scripts/tests/scratch.py
- resource: .github/workflows/ci.yml
---

# Dev Container state

## Purpose

Defines where the Dev Container keeps the state that outlives a rebuild and how
it is prepared for the non-root runtime account. Which state is shared across
instances, and the per-checkout environment rule, belong to `catalog-lifecycle`
and `agentdev-runtime-images`; this spec holds the volumes' creation and
preparation, the `.venv` link's edge cases, and the root-test launcher.

## Requirements

### Requirement: the host init creates the shared auth volume

`.devcontainer/devcontainer-init.sh` SHALL create the Docker volume
`agentdev-agents-auth-<uid>-<gid>`, named after the host user's `id -u` and
`id -g`, and write its name to `.devcontainer/.env` as `AGENTDEV_AUTH_VOLUME`.
`.devcontainer/docker-compose.yml` SHALL declare that volume `external: true`
with an explicit `name:`, so Compose adds no project prefix, and mount it at
`/var/lib/agentdev/auth`. The image SHALL set `CLAUDE_SECURESTORAGE_CONFIG_DIR`
to `/var/lib/agentdev/auth/claude`.

#### Scenario: a second worktree opens a Dev Container

- **WHEN** the same host user opens a Dev Container from a second worktree
- **THEN** its Compose project mounts the volume the first one uses, and Claude
  Code finds the existing login

### Requirement: the home volume starts empty and the bootstrap claims it

The Dev Container image SHALL define the account `agent` (1000:1000) with an
empty `/home/agent` it owns, declare `remoteUser: agent` and
`updateRemoteUserUID: true`, and mount the volume
`agentdev-home-${devcontainerId}` at `/home/agent`. The base image SHALL write
its shell `PATH` and history setup to `/etc/bash.bashrc` and
`/etc/fish/conf.d/`, never into a home. For a non-root account the bootstrap
SHALL write a validated passwordless sudoers entry, give an empty home mount to
the account, refuse a populated home another UID owns, refuse a checkout the
account cannot write with an error naming the UID and GID it needs, and refuse a
populated auth volume holding an entry another UID owns. It SHALL initialize an
empty auth volume under an exclusive lock, so only the first of several
containers writes it. A root account SHALL keep its mounts and checkout as they
are, with no claim and no sudoers entry.

#### Scenario: first start on a fresh home volume

- **WHEN** a Dev Container starts with a new home volume
- **THEN** the volume is empty and owned by the remapped account, and an
  interactive shell still gets the image's `PATH`

#### Scenario: the checkout belongs to another user

- **WHEN** the host checkout is not writable by the remapped account
- **THEN** the bootstrap fails, naming the UID and GID the checkout must allow

#### Scenario: the host user is root

- **WHEN** the host user is root, so the account keeps 1000:1000, and the
  checkout is root-owned
- **THEN** the bootstrap refuses the checkout with an error naming the UID it
  needs

### Requirement: the create phase re-owns the sibling checkout volume

The create phase SHALL re-own `/workspaces/project` recursively to the account
when it is a mount the account does not own, unless it is the open workspace
folder or the account is root.

#### Scenario: a sibling checkout volume from an earlier identity

- **WHEN** the create phase runs and `/workspaces/project` is a mount owned by
  another UID
- **THEN** it is re-owned to the account, and its uncommitted work stays
  editable

### Requirement: link-venv leaves a .venv it does not own in place

`agentdev-runtime project link-venv [PATH]` SHALL link the checkout's `.venv` to
`$AGENTDEV_VENV_ROOT/<checkout directory name>`, creating the target first, and
record the checkout's path in `<name>.checkout` beside it. It SHALL be
idempotent, SHALL replace a link into another directory under the root or a
dangling link, and SHALL leave a real `.venv` directory, or a link to an
existing path outside the root, in place with a warning. It SHALL do nothing in
deploy mode, outside a Git checkout, or while the root's parent directory is
missing; the create phase SHALL therefore create a root that lies inside the
account's home. Attach SHALL replace a real uv environment (one holding
`pyvenv.cfg`) in the workspace folder with the link. The Dev Container SHALL set
no `UV_PROJECT_ENVIRONMENT`, and its editor settings that take a path SHALL name
`${workspaceFolder}/.venv/bin/...`.

#### Scenario: the host made an environment in the mounted checkout

- **WHEN** the workspace folder holds a real `.venv` with `pyvenv.cfg` at attach
- **THEN** attach deletes it and links `.venv` to the checkout's environment
  under the root

#### Scenario: run outside a Dev Container

- **WHEN** `link-venv` runs where the root's parent directory does not exist
- **THEN** it changes nothing and exits 0

#### Scenario: two checkouts share a directory name

- **WHEN** two checkouts have the same directory name
- **THEN** both `.venv` links name the same environment

### Requirement: only link-venv runs at post-checkout

`agentdev-runtime project hooks` SHALL install pre-commit's `post-checkout` hook
type with the other hook types. This repository's `.pre-commit-config.yaml`
SHALL set `default_stages` without `post-checkout`, and its only `post-checkout`
hook SHALL be `link-venv`, which exits 0 where `agentdev-runtime` is not on
`PATH`.

#### Scenario: a worktree is added on the host

- **WHEN** `git worktree add` runs where `agentdev-runtime` is absent
- **THEN** the `post-checkout` hook succeeds and changes nothing

#### Scenario: a checkout of main

- **WHEN** a checkout switches to `main` in the Dev Container
- **THEN** no hook without its own `stages`, such as `no-commit-to-branch`, runs

### Requirement: root-only tests run through a launcher

A test that needs root SHALL carry the `requires_root` marker, and a run that is
not root SHALL skip it. `scripts/run-root-tests` SHALL refuse to start as root
and SHALL run the project environment's own Python as root through
`sudo -- env -i`, passing only `PATH`, `HOME=/root`,
`PYTHONDONTWRITEBYTECODE=1`, its own scratch root `/tmp/agentdev-root-tests`,
and the launcher flag, with `-m requires_root` and pytest's cache provider off.
Under the launcher, a root run that selects any test without the marker SHALL
fail before running. A root run without the launcher SHALL stay unrestricted.
CI's Dev Container image job SHALL run the launcher after the suite and fail
when it left a root-owned file in the checkout or the runtime account's scratch
root.

#### Scenario: the launcher selects an unmarked test

- **WHEN** `scripts/run-root-tests` is given a path holding a test without
  `requires_root`
- **THEN** pytest stops with a usage error naming it, and no test runs

#### Scenario: started as root

- **WHEN** `scripts/run-root-tests` runs as root
- **THEN** it exits 2 and suggests `pytest -m requires_root`

## Rationale

### Claude credentials shared per host user; all other state per instance

Claude Code's credentials live on one volume named after the host user's UID and
GID, and everything else on each instance's home volume. Compose's project
prefix is what isolates one instance's volumes from another's, so the credential
volume pins a literal name to make one login serve every instance. The IDs in
the name keep two host users on one engine from sharing, or locking each other
out of, one credential store. The rest of each agent's state records absolute
workspace paths, so sharing it would point one worktree's sessions at another
worktree's directories. OpenCode v2 keeps logins in its database and writes no
`auth.json`, so there is no file to share; the maintainer accepted a fresh
OpenCode login per worktree. Worktrees share one Claude credential file, and
claude.ai refresh tokens are single-use, so two processes refreshing at once can
leave one at `Login expired`; a fresh `/login` in any container recovers every
instance. This is accepted.

Rejected:

- **Sharing all agent state across instances.** It records absolute workspace
  paths.
- **A Compose-prefixed credential volume.** Every new worktree would demand a
  fresh login for each agent.
- **Copying, seeding, refreshing, or distributing agent credentials across
  workspaces.** claude.ai rotates the refresh token on refresh, so one snapshot
  copied into several workspaces stays valid only in the first that refreshes
  and the rest reach `Login expired`. A login happens by `/login` inside a
  container and persists on the shared auth volume.

### One empty home volume for a remapped non-root account

The Dev Container adopts the deploy runtime's account model: a non-root account
remapped to the host user, whose whole home is one per-instance volume that
starts empty. The image ships `/home/agent` empty because the devcontainer CLI's
UID update re-owns the account's home and fails the build when it is missing,
and anything built into a home would be copied into the volume once and never
updated by an image upgrade. Root hosts are unsupported, by the repository
owner's decision. Editor servers (`~/.vscode-server` and its siblings) persist
on the home volume with no cleanup: the owner accepted the risk of unbounded
growth and of a broken server install surviving a rebuild.

Rejected:

- **A volume on `/root`, still running as root.** The base image builds shell
  configuration, `gh` extensions, and tool state into `/root`; a volume there
  freezes all of it at the first create's image.
- **A volume on `/root` refreshed from the image on every start.** Overwrites
  the user's own edits and needs an ownership decision for each file.
- **Creating the account at container start, as deploy does.** The devcontainer
  CLI's UID update needs an account the image defines.
- **A separate `/uv` volume.** The owner chose one home volume for uv's cache,
  interpreters, and environments.
- **Per-directory state volumes.** Every new piece of state needs its own volume
  decision, and single files such as `~/.claude.json` need symlink workarounds.
- **Keeping editor servers off the home volume, or pruning old versions at
  create.** Declined by the owner.

### Each checkout's environment on the home volume, reached through a .venv link

Environments live on the home volume beside uv's cache so uv can hardlink
packages out of the cache; an in-tree `.venv` would sit on the workspace bind
mount, where uv silently falls back to copying, and on a macOS host every uv
file operation would cross VirtioFS. One environment per checkout, because
`uv run` repoints editable installs at the invoking checkout. A `.venv` link
rather than `UV_PROJECT_ENVIRONMENT`, because the variable is one value for the
whole container and uv ignores `.venv` while it is set; the link carries the
choice inside the checkout, so every `uv run` finds its own environment with no
wrapper. The mounted checkout belongs to the container: host and container
cannot share one environment, so a host working there sets its own
`UV_PROJECT_ENVIRONMENT`.

Rejected:

- **One shared environment without editable installs.** Dependencies still
  diverge between branches.
- **An in-tree `.venv` with the uv cache inside the checkout.** Hard links
  return, but all uv I/O runs on VirtioFS on macOS, and it clashes with a host
  `.venv`.
- **A per-checkout `UV_PROJECT_ENVIRONMENT`** set by a `uv` wrapper or
  `CLAUDE_ENV_FILE`. Session-scoped and brittle.
- **`UV_LINK_MODE=symlink`.** A cache clean breaks every environment.
- **A `PreToolUse` hook.** It runs on every tool call.
- **`SessionStart` and `SubagentStart` hooks in the agentdev plugin.**
  `SessionStart` runs on every session rather than once per worktree,
  `SubagentStart` fires on a dispatch rather than on a worktree's creation, and
  a session that disables the plugin gets neither.
- **Sweeping every worktree from a hook** rather than targeting the one at hand.

### Root tests run through sudo env -i from the runtime account

Root-only tests run as root from the runtime account so the suite passes as
`agent` and root never syncs or writes into `.venv`. `env -i` sets the variable
list because `sudo`'s `secure_path` would replace `PATH`, and no token is on the
list. The launcher's refusal of unmarked tests catches mistakes and is not a
security boundary; cloud session hosts, GitHub `container:` jobs, and a root Dev
Container run the whole suite as root on purpose.

Rejected:

- **`uv run` or `sudo -E` as root.** Root would sync into `.venv` or inherit
  every variable, tokens included.
