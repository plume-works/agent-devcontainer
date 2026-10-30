---
type: plan
created: 2026-10-30
release:
- features/devcontainer-home-volume
- bugs/claude-json-symlink-replaced
description: Run the Dev Container as a non-root account remapped to the host user, with its whole home on one per-instance volume and Claude and Codex credentials on a per-UID-cohort auth volume, replacing the per-directory volumes under /root; uv moves onto the home volume in both runtimes.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T16:18:33Z
sources:
- resource: docs/knowledge/data/architecture/devcontainer-home-volume.md
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: .devcontainer/devcontainer.json
- resource: .devcontainer/docker-compose.yml
- resource: .devcontainer/devcontainer-init.sh
- resource: .devcontainer/scripts/runtime-bootstrap.sh
- resource: .devcontainer/scripts/setup-agent-state.sh
- resource: .devcontainer/scripts/devcontainer-created.sh
- resource: .devcontainer/scripts/link-codex-auth.sh
- resource: docs/knowledge/data/bugs/standalone-codex-auth-unshared.md
- resource: compose.opencode.yml
- resource: ansible/roles/bash_setup/tasks/main.yml
- resource: ansible/roles/bun_setup/tasks/main.yml
- resource: ansible/roles/github_cli/tasks/main.yml
- resource: https://containers.dev/implementors/json_reference/
---

# Run the Dev Container as a non-root account with one home volume

## Context

[Dev Container home volume](../features/devcontainer-home-volume.md) is the
feature this plan implements, and [Dev Container home
volume](../architecture/devcontainer-home-volume.md) records the decision and
the rejected alternatives. The Dev Container runs as root with `/root` on the
container filesystem, so every piece of per-instance state has its own volume
(`agentdev-claude`, `agentdev-codex`, `agentdev-opencode`, `agentdev-uv`, and
the volumes holding the CBM and pre-commit caches), `~/.claude.json` is a
symlink into the `~/.claude` volume, and a cache below the bind-mounted checkout
depends on the checkout's owner, because CBM refuses a cache directory with an
ancestor another UID owns. The deploy runtime has none of this: a non-root
account whose whole home is one volume.

The owner's decisions for this plan: a non-root account; the work lands after
[Replace the runtime shell scripts with one agentdev-runtime
CLI](20261029-off-bash-migration.md), in that CLI; the account's UID and GID
match the host user through the devcontainer CLI; Claude and Codex credentials
move to a new auth volume per UID/GID cohort, so every agent logs in once again;
existing per-instance state is dropped, not migrated; the sibling checkout
volume is re-owned once so its uncommitted work survives; uv moves onto the home
volume in the Dev Container and in the deploy runtime; editor servers persist on
the home volume with no cleanup, an accepted risk.

Storing `~/.claude.json` as a file on the home volume removes the link that
[~/.claude.json stops being the volume
symlink](../bugs/claude-json-symlink-replaced.md) describes, so this plan fixes
that bug. The cohort auth volume shares Codex's login through the same
`auth.json` link that [Bug: Codex login stops being shared between standalone
projects](../bugs/standalone-codex-auth-unshared.md) reports broken, so Task 1
settles whether a login keeps the link before anything is built on it. The
account cannot write the root-owned `/workspaces`, so worktree mode relies on
the fallback parent that [Bug: git-new-branch worktree mode fails on a
standalone deployment's root-owned
/workspaces](../bugs/git-new-branch-worktree-unwritable-workspaces.md) lands
before this plan.

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

The base image's shell blocks (the `~/.local/bin` path, the `docker/bin`
wrapper, `bun`, history settings) move to system-wide files so an empty home has
them and an image upgrade updates them; the roles keep `$HOME`-relative paths,
so each account resolves its own home.

This repository's descriptor drops every per-directory state mount and the
`/root` paths, and its host initializer names the shared auth volume after the
host user's UID and GID. Both runtimes drop the `/uv` volume: uv's cache and
Python installs take uv's defaults under the home, and `UV_PROJECT_ENVIRONMENT`
stays set, to a path under the home, because uv's own default is `.venv` inside
the checkout.

The rejected alternatives are recorded in the architecture document.

Assumption: the devcontainer CLI applies `updateRemoteUserUID` to a
Compose-based configuration and to image-metadata `remoteUser`. Task 2's tests
and Task 10's check confirm it; if either fails, the plan returns to revise mode
before Task 6.

Assumption: a Codex login writes through the `~/.codex/auth.json` link rather
than replacing it. Task 1 settles it; if a login replaces the link, the plan
returns to revise mode before Task 4.

## Implementation Steps

### Task 1: Settle whether a Codex login keeps the auth.json link

**Files:** none (a running Dev Container or deploy container)

- [ ] In a container whose `~/.codex/auth.json` is the link into the shared auth
  volume, run `codex login` as the runtime user, then
  `test -L ~/.codex/auth.json`, and record the Codex version and the result
  under `## Verification results`.

### Task 2: Give the Dev Container image a home-less agent account

**Files:** Modify: `docker/devcontainer/agentdev-devcontainer.Dockerfile`,
`scripts/tests/test_agentdev_devcontainer_image.py`

- [ ] The image removes the stock `ubuntu` account and creates group and account
  `agent` (1000:1000, shell `/bin/bash`, home `/home/agent`) without creating
  the home directory.
- [ ] The image environment sets `AGENTDEV_USER=agent`,
  `AGENTDEV_HOME=/home/agent`,
  `AGENTDEV_AGENTS_AUTH_DIR=/var/lib/agentdev/auth`,
  `CLAUDE_SECURESTORAGE_CONFIG_DIR=/var/lib/agentdev/auth/claude`,
  `CBM_CACHE_DIR=/home/agent/.cache/codebase-memory-mcp`, and
  `/home/agent/.local/bin` on `PATH`; no default names `/root`.
- [ ] `devcontainer.metadata` adds `"remoteUser": "agent"`,
  `"updateRemoteUserUID": true`, and a volume `agentdev-home-${devcontainerId}`
  at `/home/agent`.
- [ ] Image tests assert the account has no home directory in the image, the
  metadata carries the three entries, and `devcontainer up` on a Linux host with
  a checkout owned by a non-1000 UID runs `id -u` in the container as that UID.

### Task 3: Move the base image's shell setup out of root's home

**Files:** Modify: `ansible/roles/bash_setup/tasks/main.yml`,
`ansible/roles/bun_setup/tasks/main.yml`,
`ansible/roles/github_cli/tasks/main.yml`, their `defaults/main.yml`,
`docker/base/agentdev-base.Dockerfile`

- [ ] Each role's managed bash and fish blocks take their target file from a
  role variable that defaults to the current `{{ user_home }}` path, so host
  provisioning is unchanged.
- [ ] The base image build points those variables at `/etc/bash.bashrc` and
  `/etc/fish/conf.d/`, and an interactive shell of an account with an empty home
  has `~/.local/bin`, the checkout's `docker/bin`, and `bun` on `PATH`.

### Task 4: Bootstrap the Dev Container profile's instance storage

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

### Task 5: Store ~/.claude.json as a file on the home volume

**Files:** Modify:
`py_packages/agentdev_runtime/agentdev_runtime/claude_state.py`,
`py_packages/agentdev_runtime/agentdev_runtime/agent_state.py`,
`py_packages/agentdev_runtime/tests/test_claude_state.py`

- [ ] `agentdev-runtime state create` no longer links `~/.claude.json`. A home
  where it is a symlink to `~/.claude/claude.json` has the link replaced by a
  regular file with the target's content, and the target removed.
- [ ] The CBM install edits `~/.claude.json` in place; the fold-back around a
  symlink is removed.

### Task 6: Re-own the sibling checkout volume once

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py`,
`scripts/tests/test_agentdev_devcontainer_lifecycle.py`

- [ ] `agentdev-runtime lifecycle created`, for a non-root account, re-owns
  `/workspaces/project` recursively when it is a mount owned by another UID, and
  leaves it untouched when the account already owns it.

### Task 7: Point this repository's descriptor at the home volume

**Files:** Modify: `.devcontainer/devcontainer.json`,
`.devcontainer/docker-compose.yml`, `.devcontainer/devcontainer-init.sh`

- [ ] `devcontainer.json` drops the `agentdev-claude`, `agentdev-codex`,
  `agentdev-opencode`, `agentdev-uv`, `agentdev-pre-commit`, and `agentdev-cbm`
  mounts, and the `CLAUDE_SECURESTORAGE_CONFIG_DIR`, `CBM_CACHE_DIR`,
  `PRE_COMMIT_HOME`, `UV_CACHE_DIR`, and `UV_PYTHON_INSTALL_DIR` overrides, so
  uv's cache and Python installs and pre-commit use their defaults under the
  home. `UV_PROJECT_ENVIRONMENT` is
  `/home/agent/.local/share/uv/venvs/ws-project`. `agentdev-project` stays.
- [ ] `devcontainer-init.sh` creates `agentdev-agents-auth-<uid>-<gid>` from the
  host user's `id -u` and `id -g` and writes its name to `.env`, and
  `docker-compose.yml` mounts it at `/var/lib/agentdev/auth`.
- [ ] The MCP directory and secrets-engine socket targets move from `/root` to
  `/home/agent`.

### Task 8: Move the deploy runtime's uv state onto its home volume

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

### Task 9: Migrate template consumers

**Files:** Modify: the `template-consume` skill's update guidance under
`.agents/plugins/agentdev/skills/template-consume/`,
`scripts/tests/test_template_consume_migration.py`

- [ ] An update from a pre-change template removes the per-directory state
  mounts and `/root` paths from the consumer's descriptor and states that agent
  state and logins reset once.

### Task 10: Accept a rebuilt Dev Container on a host-owned checkout

**Files:** none (a Linux host whose checkout is owned by the host user)

- [ ] A rebuilt Dev Container runs as `agent` with the host user's UID and GID.
- [ ] After `docker restart`, the supervisor reports `cbm` ready.
- [ ] `agentdev:*` skills resolve in Claude Code.
- [ ] Claude and Codex stay logged in across a second rebuild.
- [ ] `git-new-branch --worktree` from the checkout creates its worktree as
  `agent`.

### Task 11: Record the shipped model

**Files:** Modify:
`docs/knowledge/data/architecture/devcontainer-home-volume.md`,
`docs/knowledge/data/architecture/agent-auth-persistence.md`,
`docs/knowledge/data/architecture/cbm-daemon-lifecycle.md`,
`docs/knowledge/data/features/persist-pre-commit-cache.md`, affected
`docs/knowledge/data/codebase/` map docs

- [ ] The architecture document describes the shipped account and volumes; the
  auth and CBM documents and the pre-commit feature name the home volume and the
  cohort auth volume instead of the per-directory volumes; the map is refreshed.

## Spec changes

### [Catalog lifecycle](../spec/catalog-lifecycle.md)

``` markdown
## MODIFIED Requirements

### Requirement: the catalog is installed at image build time and again by postCreateCommand

The `agentdev` catalog staged at `$AGENTDEV_CATALOG_DIR` SHALL be installed into
each agent's plugin state during the `agentdev-base` build, at Claude user
scope, via Codex's own registration, and by registering the catalog's OpenCode
bridge plugin in the user's OpenCode config, so a consumer that runs the image
without lifecycle commands resolves `agentdev:*` skills.
`agentdev-devcontainer`'s `postCreateCommand` SHALL also install it into the
runtime account's home volume, which starts empty and receives no image
content. `~/.claude.json` SHALL be a regular file on that volume, which the CBM
install edits in place.

#### Scenario: the image runs with no volumes and no lifecycle hooks

- **WHEN** a container starts from `agentdev-base` without client-state volumes
  and no lifecycle command runs
- **THEN** the catalog installed during the image build is present, an
  `agentdev:*` skill resolves in Claude Code and Codex, and OpenCode loads the
  staged bridge plugin and lists the catalog's skills.

#### Scenario: a devcontainer starts for the first time on a fresh home volume

- **WHEN** `postCreateCommand` runs, `$AGENTDEV_CATALOG_DIR` exists, and the
  home volume is empty
- **THEN** the staged catalog is installed at Claude user scope, into Codex, and
  into the OpenCode user config on the home volume, and `~/.claude.json` is a
  regular file holding the CBM install's MCP entry and no image content.

#### Scenario: a devcontainer starts with a catalog already installed on its home volume

- **WHEN** the home volume already holds a prior install and `~/.claude.json`,
  and the container is recreated
- **THEN** `~/.claude.json`'s content is preserved (the CBM install edits its
  MCP entry; Claude may append bootstrap fields, so the guarantee is content
  preservation, not byte-identity), and `postCreateCommand` re-applies the
  catalog install every time the container is created, so it is never silently
  stale.

#### Scenario: a home volume still holds the ~/.claude.json link

- **WHEN** `~/.claude.json` is a symlink to `~/.claude/claude.json`
- **THEN** it is replaced by a regular file with the link target's content, and
  the target is removed.

#### Scenario: the user has their own Codex agents

- **WHEN** `~/.codex/agents/` holds `codebase-memory.toml` before an install
- **THEN** the file is unchanged after the install.

### Requirement: only agent credentials are shared across worktrees

The shared auth volume SHALL hold only Claude's and Codex's authentication
state, mounted at `/var/lib/agentdev/auth/<agent>`, and SHALL be named after the
host user's UID and GID, so only containers whose account has the same IDs
share it. All other client state SHALL live on each instance's home volume.

#### Scenario: two worktrees of the same repository are opened as separate devcontainers

- **WHEN** both attach as the same host user
- **THEN** each gets its own catalog install on its own home volume but shares
  the same logged-in Claude and Codex credentials on the shared auth volume.

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
- Task 1's recorded Codex login result.
- Task 10's acceptance on a Linux host with a host-owned checkout.

## Out of scope

- Migrating existing per-instance state or logins; they reset once.
- Cleaning editor servers on the home volume (accepted risk in the architecture
  document).
- The deploy runtime's account model, which already works this way; it changes
  only by dropping the `~/.claude.json` link and the `/uv` volume. A deploy
  instance's existing `/uv` volume is no longer mounted, and its uv cache and
  project venv are rebuilt once.
- GitHub Actions container jobs, which run as the job's user and keep the root
  branch of the create phase.

## Key references

Verified anchor points (line numbers as of 2026-10-30). The off-bash migration
ports each script to the `agentdev_runtime` module named in its plan.

- `docker/devcontainer/agentdev-devcontainer.Dockerfile:30` —
  `AGENTDEV_USER=root`
- `docker/devcontainer/agentdev-devcontainer.Dockerfile:31` —
  `AGENTDEV_HOME=/root`
- `docker/devcontainer/agentdev-devcontainer.Dockerfile:36` — `CBM_CACHE_DIR`
- `docker/devcontainer/agentdev-devcontainer.Dockerfile:41` —
  `devcontainer.metadata`
- `docker/deploy/agentdev-deploy.Dockerfile:16` — `userdel --remove ubuntu`
- `docker/base/agentdev-base.Dockerfile:92` — `PATH` with `/root/.local/bin`
- `.devcontainer/scripts/runtime-bootstrap.sh:96` — `claim_instance_dir`
- `.devcontainer/scripts/runtime-bootstrap.sh:126` — `prepare_shared_auth`
- `.devcontainer/scripts/runtime-bootstrap.sh:156` — `bootstrap_deploy`
- `.devcontainer/scripts/runtime-bootstrap.sh:190` — `bootstrap_devcontainer`
- `.devcontainer/scripts/setup-agent-state.sh:15` — `link_claude_json`
- `.devcontainer/scripts/runtime-paths.sh:10` — `agentdev_claude_json`
- `.devcontainer/scripts/devcontainer-created.sh:16` — `claim_ancestors`
- `.devcontainer/scripts/devcontainer-created.sh:25` — `claim_mounts`
- `.devcontainer/scripts/devcontainer-created.sh:34` — `cmd_create`
- `docker/devcontainer/supervisord.conf:54` — `user=%(ENV_AGENTDEV_USER)s`
- `.devcontainer/devcontainer.json:36` — `CLAUDE_SECURESTORAGE_CONFIG_DIR`
- `.devcontainer/devcontainer.json:61` — `agentdev-uv` mount
- `.devcontainer/devcontainer.json:67` — `agentdev-pre-commit` mount
- `.devcontainer/devcontainer.json:73` — `agentdev-cbm` mount
- `.devcontainer/devcontainer.json:89` — `agentdev-claude` mount
- `.devcontainer/devcontainer.json:101` — `agentdev-codex` mount
- `.devcontainer/devcontainer.json:109` — `agentdev-opencode` mount
- `.devcontainer/devcontainer.json:116` — `agentdev-project` mount
- `.devcontainer/docker-compose.yml:103` — `agentdev-agents-auth` mount
- `.devcontainer/devcontainer-init.sh:24` —
  `docker volume create agentdev-agents-auth`
- `.devcontainer/devcontainer-init.sh:56` — `CONTAINER_MCP_DIR`
- `compose.opencode.yml:45` — `uv:/uv` mount
- `docker/deploy/agentdev-deploy.Dockerfile:45` — `UV_CACHE_DIR=/uv/cache`
- `.devcontainer/scripts/runtime-bootstrap.sh:166` —
  `claim_instance_dir "$uv_dir"`
- `scripts/tests/test_agent_runtime_compose.py:21` — `INSTANCE_TARGETS`
- `.devcontainer/scripts/link-codex-auth.sh:35` — the `auth.json` link Task 1
  tests
- `docker/base/agentdev-base.Dockerfile:84` — `WORKDIR`, which creates the
  root-owned `/workspaces`
- `ansible/roles/bash_setup/tasks/main.yml:5` — `.bashrc` target
- `ansible/roles/bun_setup/tasks/main.yml:30` — `.bashrc` target
- `ansible/roles/github_cli/tasks/main.yml:53` — `.bashrc` target
