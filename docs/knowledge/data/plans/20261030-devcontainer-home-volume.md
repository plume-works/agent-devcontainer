---
type: plan
created: 2026-10-30
release:
- features/devcontainer-home-volume
- bugs/claude-json-symlink-replaced
description: Run the Dev Container as a non-root account remapped to the host user, with its whole home on one per-instance volume and Claude credentials on a per-UID-cohort auth volume, replacing the per-directory volumes under /root; uv moves onto the home volume in both runtimes.
sources:
- resource: docs/knowledge/data/architecture/devcontainer-home-volume.md
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: .devcontainer/devcontainer.json
- resource: .devcontainer/docker-compose.yml
- resource: .devcontainer/devcontainer-init.sh
- resource: py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: compose.opencode.yml
- resource: py_packages/agentdev_runtime/agentdev_runtime/cbm_purge.py
- resource: ansible/roles/bash_setup/tasks/main.yml
- resource: ansible/roles/bun_setup/tasks/main.yml
- resource: https://containers.dev/implementors/json_reference/
rank: 600
---

# Run the Dev Container as a non-root account with one home volume

## Context

[Dev Container home volume](../features/devcontainer-home-volume.md) is the
feature this plan implements, and [Dev Container home
volume](../architecture/devcontainer-home-volume.md) records the decision and
the rejected alternatives. The Dev Container runs as root with `/root` on the
container filesystem, so every piece of per-instance state has its own volume
(`agentdev-claude`, `agentdev-opencode`, `agentdev-uv`, and the volume holding
the pre-commit cache), and `~/.claude.json` is a symlink into the `~/.claude`
volume. The deploy runtime is a non-root account whose home is one volume; it
keeps only the `/uv` volume and the `~/.claude.json` link.

The owner's decisions for this plan: a non-root account; the work lands after
[Replace the runtime shell scripts with one agentdev-runtime
CLI](20261029-off-bash-migration.md), in that CLI; the account's UID and GID
match the host user through the devcontainer CLI; Claude credentials move to a
new auth volume per UID/GID cohort, so Claude logs in once again; existing
per-instance state is dropped, not migrated; the sibling checkout volume is
re-owned once so its uncommitted work survives; uv moves onto the home volume in
the Dev Container and in the deploy runtime; editor servers persist on the home
volume with no cleanup, an accepted risk.

Storing `~/.claude.json` as a file on the home volume removes the link that
[~/.claude.json stops being the volume
symlink](../bugs/claude-json-symlink-replaced.md) describes, so this plan fixes
that bug. The account cannot write the root-owned `/workspaces`, so worktree
mode uses the checkout's `.worktrees/` directory.

## Approach

The Dev Container profile converges on deploy's account handling. The image
deletes the stock `ubuntu` account and creates `agent` (1000:1000) with no home
directory, at image build time so the devcontainer CLI's UID update has an
account to remap (part of the Assumption below). The image metadata declares
`remoteUser: agent` and `updateRemoteUserUID: true`, and mounts a per-instance
home volume named after `${devcontainerId}` at `/home/agent`, as it already
mounts the nested engine's storage. The container's own user stays root, so PID
1 is still the supervisor; supervisord already runs every user service as
`AGENTDEV_USER`.

The Dev Container bootstrap gains deploy's storage steps for the account it
reads from `passwd`: claim the empty home mount root, write the sudoers entry,
take the shared-auth lock, and check the workspace is writable. It still never
creates the account. With the home on one volume, `~/.claude.json` is an
ordinary file in both profiles; the link step goes, and a home that still holds
the link (a deploy home volume) has it replaced by the file it pointed to.

The base image's shell blocks (the `~/.local/bin` path, `bun`, history settings)
move to system-wide files so an empty home has them and an image upgrade updates
them; the roles keep `$HOME`-relative paths, so each account resolves its own
home.

This repository's descriptor drops every per-directory state mount and the
`/root` paths, and its host initializer names the shared auth volume after the
host user's UID and GID. Both runtimes drop the `/uv` volume: uv's cache and
Python installs take uv's defaults under the home, and `UV_PROJECT_ENVIRONMENT`
stays set, to a path under the home, because uv's own default is `.venv` inside
the checkout.

The rejected alternatives are recorded in the architecture document.

Assumption: the devcontainer CLI applies `updateRemoteUserUID` to a
Compose-based configuration and to image-metadata `remoteUser`. Task 1's tests
and Task 9's check confirm it; if either fails, the plan returns to revise mode
before Task 5.

## Implementation Steps

### Task 1: Give the Dev Container image a home-less agent account

**Files:** Modify: `docker/devcontainer/agentdev-devcontainer.Dockerfile`,
`scripts/tests/test_agentdev_devcontainer_image.py`

- [ ] The image removes the stock `ubuntu` account and creates group and account
  `agent` (1000:1000, shell `/bin/bash`, home `/home/agent`) without creating
  the home directory.
- [ ] The image environment sets `AGENTDEV_USER=agent`,
  `AGENTDEV_HOME=/home/agent`,
  `AGENTDEV_AGENTS_AUTH_DIR=/var/lib/agentdev/auth`,
  `CLAUDE_SECURESTORAGE_CONFIG_DIR=/var/lib/agentdev/auth/claude`, and
  `/home/agent/.local/bin` on `PATH`; no default names `/root`.
- [ ] `devcontainer.metadata` adds `"remoteUser": "agent"`,
  `"updateRemoteUserUID": true`, and a volume `agentdev-home-${devcontainerId}`
  at `/home/agent`.
- [ ] Image tests assert the account has no home directory in the image, the
  metadata carries the three entries, and `devcontainer up` on a Linux host with
  a checkout owned by a non-1000 UID runs `id -u` in the container as that UID.

### Task 2: Move the base image's shell setup out of root's home

**Files:** Modify: `ansible/roles/bash_setup/tasks/main.yml`,
`ansible/roles/bun_setup/tasks/main.yml`, their `defaults/main.yml`,
`docker/base/agentdev-base.Dockerfile`

- [ ] Each role's managed bash and fish blocks take their target file from a
  role variable that defaults to the current `{{ user_home }}` path, so host
  provisioning is unchanged.
- [ ] The base image build points those variables at `/etc/bash.bashrc` and
  `/etc/fish/conf.d/`, and an interactive shell of an account with an empty home
  has `~/.local/bin` and `bun` on `PATH`.

### Task 3: Bootstrap the Dev Container profile's instance storage

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py`,
`scripts/tests/test_agent_runtime_identity.py`

- [ ] `agentdev-runtime bootstrap` in the Dev Container profile, for a non-root
  account read from `passwd`, claims the home mount root when it is empty and
  refuses when another identity owns a populated one, writes the sudoers entry,
  takes the shared-auth lock and initializes an empty auth volume, and checks
  the workspace is writable, naming the UID it must be writable by on refusal.
- [ ] A root account keeps the root Dev Container bootstrap (account and mounts
  accepted as given, no home claim or sudoers entry), so a consumer overriding
  `AGENTDEV_USER=root` still starts.

### Task 4: Store ~/.claude.json as a file on the home volume

**Files:** Modify:
`py_packages/agentdev_runtime/agentdev_runtime/claude_state.py`,
`py_packages/agentdev_runtime/agentdev_runtime/agent_state.py`,
`py_packages/agentdev_runtime/tests/test_claude_state.py`,
`py_packages/agentdev_runtime/tests/test_cbm_purge.py`

- [ ] `agentdev-runtime state create` no longer links `~/.claude.json`. A home
  where it is a symlink to `~/.claude/claude.json` has the link replaced by a
  regular file with the target's content, and the target removed.
- [ ] `cbm_purge.purge` runs after that replacement, so a deploy home holding a
  codebase-memory-mcp entry behind the link loses the entry from the regular
  file, and a test runs that case.

### Task 5: Re-own the sibling checkout volume once

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py`,
`scripts/tests/test_agentdev_devcontainer_lifecycle.py`

- [ ] `agentdev-runtime lifecycle created`, for a non-root account, re-owns
  `/workspaces/project` recursively when it is a mount owned by another UID, and
  leaves it untouched when the account already owns it.

### Task 6: Point this repository's descriptor at the home volume

**Files:** Modify: `.devcontainer/devcontainer.json`,
`.devcontainer/docker-compose.yml`, `.devcontainer/devcontainer-init.sh`

- [ ] `devcontainer.json` drops the `agentdev-claude`, `agentdev-opencode`,
  `agentdev-uv`, and `agentdev-pre-commit` mounts, and the
  `CLAUDE_SECURESTORAGE_CONFIG_DIR`, `PRE_COMMIT_HOME`, `UV_CACHE_DIR`, and
  `UV_PYTHON_INSTALL_DIR` overrides, so uv's cache and Python installs and
  pre-commit use their defaults under the home. `UV_PROJECT_ENVIRONMENT` is
  `/home/agent/.local/share/uv/venvs/ws-project`. `agentdev-project` stays.
- [ ] `devcontainer-init.sh` creates `agentdev-agents-auth-<uid>-<gid>` from the
  host user's `id -u` and `id -g` and writes its name to `.env`, and
  `docker-compose.yml` mounts it at `/var/lib/agentdev/auth`.
- [ ] The MCP directory and secrets-engine socket targets move from `/root` to
  `/home/agent`.

### Task 7: Move the deploy runtime's uv state onto its home volume

**Files:** Modify: `compose.opencode.yml`,
`docker/deploy/agentdev-deploy.Dockerfile`,
`py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py`,
`scripts/tests/test_agent_runtime_compose.py`,
`scripts/tests/test_agent_runtime_identity.py`

- [ ] `compose.opencode.yml` mounts no `/uv` volume and declares none.
- [ ] The deploy image drops `UV_CACHE_DIR` and `UV_PYTHON_INSTALL_DIR`, and
  sets `UV_PROJECT_ENVIRONMENT=/home/agent/.local/share/uv/venvs/project`.
- [ ] The deploy bootstrap no longer requires or claims a `/uv` mount; the
  compose test's instance targets are `/home/agent` and `/var/lib/docker`.

### Task 8: Migrate template consumers

**Files:** Modify: the `template-consume` skill's update guidance under
`.agents/plugins/agentdev/skills/template-consume/`,
`scripts/tests/test_template_consume_migration.py`

- [ ] An update from a pre-change template removes the per-directory state
  mounts and `/root` paths from the consumer's descriptor and states that agent
  state and logins reset once.

### Task 9: Accept a rebuilt Dev Container on a host-owned checkout

**Files:** none (a Linux host whose checkout is owned by the host user)

- [ ] A rebuilt Dev Container runs as `agent` with the host user's UID and GID.
- [ ] After `docker restart`, the supervisor reports its required services
  ready.
- [ ] `agentdev:*` skills resolve in Claude Code.
- [ ] Claude stays logged in across a second rebuild.
- [ ] `git-new-branch --worktree` from the checkout creates its worktree as
  `agent`.

### Task 10: Record the shipped model

**Files:** Modify:
`docs/knowledge/data/architecture/devcontainer-home-volume.md`,
`docs/knowledge/data/architecture/agent-auth-persistence.md`,
`docs/knowledge/data/features/persist-pre-commit-cache.md`

- [ ] The architecture document describes the shipped account and volumes; the
  auth document and the pre-commit feature name the home volume and the cohort
  auth volume instead of the per-directory volumes.

## Spec changes

### [Catalog lifecycle](../spec/catalog-lifecycle.md)

``` markdown
## MODIFIED Requirements

### Requirement: the catalog is installed at image build time and again by postCreateCommand

The `agentdev` catalog staged at `$AGENTDEV_CATALOG_DIR` SHALL be installed into
each agent's plugin state during the `agentdev-base` build, at Claude user
scope and by registering the catalog's OpenCode
bridge plugin in the user's OpenCode config, so a consumer that runs the image
without lifecycle commands resolves `agentdev:*` skills.
`agentdev-devcontainer`'s `postCreateCommand` SHALL also install it into the
runtime account's home volume, which starts empty and receives no image
content. `~/.claude.json` SHALL be a regular file on that volume.

#### Scenario: the image runs with no volumes and no lifecycle hooks

- **WHEN** a container starts from `agentdev-base` without client-state volumes
  and no lifecycle command runs
- **THEN** the catalog installed during the image build is present, an
  `agentdev:*` skill resolves in Claude Code, and OpenCode loads the
  staged bridge plugin and lists the catalog's skills.

#### Scenario: a devcontainer starts for the first time on a fresh home volume

- **WHEN** `postCreateCommand` runs, `$AGENTDEV_CATALOG_DIR` exists, and the
  home volume is empty
- **THEN** the staged catalog is installed at Claude user scope and
  into the OpenCode user config on the home volume, and `~/.claude.json` is a
  regular file holding no image content.

#### Scenario: a devcontainer starts with a catalog already installed on its home volume

- **WHEN** the home volume already holds a prior install and `~/.claude.json`,
  and the container is recreated
- **THEN** `~/.claude.json`'s content is preserved (Claude may append bootstrap
  fields, so the guarantee is content preservation, not byte-identity), and `postCreateCommand` re-applies the
  catalog install every time the container is created, so it is never silently
  stale.

#### Scenario: a home volume still holds the ~/.claude.json link

- **WHEN** `~/.claude.json` is a symlink to `~/.claude/claude.json`
- **THEN** it is replaced by a regular file with the link target's content, and
  the target is removed.

### Requirement: the create phase clears codebase-memory-mcp's leftovers

The create phase of both profiles SHALL remove what
`codebase-memory-mcp install` wrote into persisted configuration, after any
`~/.claude.json` link is replaced by a regular file: its hooks in Claude's
`settings.json`, its MCP entries in `claude.json` and OpenCode's config, its
marked blocks in OpenCode's `AGENTS.md` and `plugins/cbm-augment.ts`, its agents,
skill, and hook scripts, and its binary and cache in the home. It SHALL leave
every other entry and file in place, SHALL NOT rewrite a file that holds nothing
of CBM's, and SHALL NOT fail the create phase over a file it cannot read. The
decision is [No code-graph index](../../../../openspec/specs/catalog-lifecycle/spec.md#rationale).

#### Scenario: a volume holds a CBM install beside the user's configuration

- **WHEN** the create phase runs on a volume holding CBM's hooks and entries
  next to the user's own hooks, MCP servers, agents, and instructions
- **THEN** only CBM's are removed.

#### Scenario: a home holds a CBM entry behind the ~/.claude.json link

- **WHEN** `~/.claude.json` is a symlink to a file holding CBM's MCP entry
- **THEN** `~/.claude.json` is a regular file without that entry, and the user's
  other content is preserved.

#### Scenario: a home holds nothing of CBM's

- **WHEN** the create phase runs on a home with no CBM install
- **THEN** no file is rewritten or created.

#### Scenario: a configuration file cannot be read

- **WHEN** a file the cleanup edits is malformed
- **THEN** that file is left as it is, a warning names the failure, the other
  cleanup steps still run, and the create phase continues.

### Requirement: only agent credentials are shared across worktrees

The shared auth volume SHALL hold only Claude's authentication
state, mounted at `/var/lib/agentdev/auth/<agent>`, and SHALL be named after the
host user's UID and GID, so only containers whose account has the same IDs
share it. All other client state SHALL live on each instance's home volume.

#### Scenario: two worktrees of the same repository are opened as separate devcontainers

- **WHEN** both attach as the same host user
- **THEN** each gets its own catalog install on its own home volume but shares
  the same logged-in Claude credentials on the shared auth volume.

#### Scenario: two host users open Dev Containers on one engine

- **WHEN** their UID/GID pairs differ
- **THEN** each container mounts its own auth volume and neither reads the
  other's credentials.
```

### [Claude Remote Control](../spec/claude-remote-control.md)

The verification procedure SHALL check the credential store at
`/var/lib/agentdev/auth/claude` in place of `/root/.agents-auth/claude`.

### [agentdev runtime images](../spec/agentdev-runtime-images.md)

The Dev Container image SHALL run its user services, lifecycle commands, and
editor sessions as a non-root account remapped to the host user's UID and GID,
with its home on one per-instance volume.

## Depends on

[Replace the runtime shell scripts with one agentdev-runtime
CLI](20261029-off-bash-migration.md)

[Narrow the image build context](20261102-narrow-image-build-context.md)

## Verification

- `uv run pytest scripts/tests/test_agentdev_devcontainer_image.py scripts/tests/test_agent_runtime_identity.py scripts/tests/test_agentdev_devcontainer_lifecycle.py scripts/tests/test_template_consume_migration.py`
  and the `agentdev_runtime` package tests pass.
- In a rebuilt Dev Container: `id` reports `agent` with the host UID;
  `findmnt /home/agent` shows the home volume; `findmnt` shows no mount below
  `/root` and none below the workspace except `agentdev-project`;
  `test -f ~/.claude.json && ! test -L ~/.claude.json`.
- `docker restart` of the container ends with
  `runtime-supervisor: all services are ready`.
- `uv run pytest scripts/tests/test_agent_runtime_compose.py` passes, and a
  deploy container started from `compose.opencode.yml` reaches ready with no
  `/uv` mount and its project venv under `/home/agent/.local/share/uv/venvs`.
- Task 9's acceptance on a Linux host with a host-owned checkout.

## Out of scope

- Migrating existing per-instance state or logins; they reset once.
- Cleaning editor servers on the home volume (accepted risk in the architecture
  document).
- The deploy runtime's account model, which already works this way; it changes
  only by dropping the `~/.claude.json` link and the `/uv` volume. A deploy
  instance's existing `/uv` volume is no longer mounted, and its uv cache and
  project venv are rebuilt once.
- GitHub Actions container jobs, which run as root and keep the create phase's
  root path; Task 3 and Task 5 act only for a non-root account.

## Key references

- `docker/devcontainer/agentdev-devcontainer.Dockerfile › "AGENTDEV_USER=root"`
  — `AGENTDEV_USER=root`
- `docker/devcontainer/agentdev-devcontainer.Dockerfile › "AGENTDEV_HOME=/root"`
  — `AGENTDEV_HOME=/root`
- `docker/devcontainer/agentdev-devcontainer.Dockerfile › "LABEL devcontainer.metadata="`
  — `devcontainer.metadata`
- `docker/deploy/agentdev-deploy.Dockerfile › "RUN userdel --remove ubuntu"` —
  `userdel --remove ubuntu`
- `docker/deploy/agentdev-deploy.Dockerfile › "UV_CACHE_DIR=/uv/cache"` —
  `UV_CACHE_DIR=/uv/cache`
- `docker/base/agentdev-base.Dockerfile › "/root/.local/bin:$PATH"` — `PATH`
  with `/root/.local/bin`
- `docker/base/agentdev-base.Dockerfile › "WORKDIR $WORKSPACE_FOLDER"` —
  `WORKDIR`, which creates the root-owned `/workspaces`
- `py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py::Deploy.ensure_sudo`
  — `ensure_sudo`
- `py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py::Deploy.claim_instance_dir`
  — `claim_instance_dir`
- `py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py::Deploy.validate_workspace`
  — `validate_workspace`
- `py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py::Deploy.prepare_shared_auth`
  — `prepare_shared_auth`
- `py_packages/agentdev_runtime/agentdev_runtime/agent_state.py::link_claude_json`
  — `link_claude_json`
- `py_packages/agentdev_runtime/agentdev_runtime/agent_state.py::create` —
  `create`
- `py_packages/agentdev_runtime/agentdev_runtime/agent_state.py::create` —
  `cbm_purge.purge`
- `py_packages/agentdev_runtime/agentdev_runtime/settings.py::VARIABLES` —
  `AGENTDEV_CLAUDE_JSON`
- `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py::claim_mounts` —
  `claim_mounts`
- `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py::created` —
  `created`
- `docker/devcontainer/supervisord.conf › "user=%(ENV_AGENTDEV_USER)s"` —
  `user=%(ENV_AGENTDEV_USER)s`
- `.devcontainer/devcontainer.json › "CLAUDE_SECURESTORAGE_CONFIG_DIR"` —
  `CLAUDE_SECURESTORAGE_CONFIG_DIR`
- `.devcontainer/devcontainer.json › "agentdev-uv"` — `agentdev-uv` mount
- `.devcontainer/devcontainer.json › "agentdev-pre-commit"` —
  `agentdev-pre-commit` mount
- `.devcontainer/devcontainer.json › "agentdev-claude"` — `agentdev-claude`
  mount
- `.devcontainer/devcontainer.json › "agentdev-opencode"` — `agentdev-opencode`
  mount
- `.devcontainer/devcontainer.json › "agentdev-project"` — `agentdev-project`
  mount
- `.devcontainer/docker-compose.yml#volumes.agentdev-agents-auth.external` —
  `agentdev-agents-auth` mount
- `.devcontainer/devcontainer-init.sh › "docker volume create agentdev-agents-auth >/dev/null"`
  — `docker volume create agentdev-agents-auth`
- `.devcontainer/devcontainer-init.sh` — `CONTAINER_MCP_DIR`
- `compose.opencode.yml › "uv:/uv"` — `uv:/uv` mount
- `scripts/tests/test_agent_runtime_compose.py::INSTANCE_TARGETS` —
  `INSTANCE_TARGETS`
- `ansible/roles/bash_setup/tasks/main.yml › "user_home }}/.bashrc"` — `.bashrc`
  target
- `ansible/roles/bun_setup/tasks/main.yml › "user_home }}/.bashrc"` — `.bashrc`
  target
