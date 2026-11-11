---
type: plan
stage: done
completed: 2026-11-11
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
deletes the stock `ubuntu` account and creates `agent` (1000:1000) with an empty
`/home/agent` it owns, at image build time so the devcontainer CLI's UID update
has an account to remap (part of the Assumption below). The directory exists
because that update runs `chown -R` on the account's home and fails the build
when the home is missing; it holds nothing, so the home volume still starts
empty. The image metadata declares `remoteUser: agent` and
`updateRemoteUserUID: true`, and mounts a per-instance home volume named after
`${devcontainerId}` at `/home/agent`, as it already mounts the nested engine's
storage. The container's own user stays root, so PID 1 is still the supervisor;
supervisord already runs every user service as `AGENTDEV_USER`.

The Dev Container bootstrap gains deploy's storage steps for the account it
reads from `passwd`: claim the empty home mount root, write the sudoers entry,
take the shared-auth lock, and check the workspace is writable. It still never
creates the account. With the home on one volume, `~/.claude.json` is an
ordinary file in both profiles; the link step goes, and a home that still holds
the link (a deploy home volume) has it replaced by the file it pointed to.

The create phase needs what the bootstrap prepares, so it runs where deploy's
`prepare` runs: as a supervised oneshot after the bootstrap and the keyring,
once per container, and core, so readiness waits for it. `postCreateCommand`
only waits for it, and fails when the runtime fails first. The image label sets
`DEV_WORKSPACE_FOLDER` through `containerEnv` instead of `remoteEnv`, so PID 1
and every supervised program see the editor's workspace folder.

The base image's shell blocks (the `~/.local/bin` path, `bun`, history settings)
move to system-wide files so an empty home has them and an image upgrade updates
them; the roles keep `$HOME`-relative paths, so each account resolves its own
home.

This repository's descriptor drops every per-directory state mount and the
`/root` paths, and its host initializer names the shared auth volume after the
host user's UID and GID. Both runtimes drop the `/uv` volume: uv's cache and
Python installs take uv's defaults under the home. The Dev Container keeps one
environment per checkout, so `AGENTDEV_VENV_ROOT` moves to
`/home/agent/.local/share/uv/venvs`, beside uv's cache on the same volume so
packages stay hardlinked, and it sets no `UV_PROJECT_ENVIRONMENT`. The image
sets that root, so a consumer whose descriptor names none gets it too. The
deploy runtime serves one checkout and keeps `UV_PROJECT_ENVIRONMENT` set, to a
path under the home, because uv's own default is `.venv` inside the checkout.

The rejected alternatives are recorded in the architecture document.

Assumption: the devcontainer CLI applies `updateRemoteUserUID` to a
Compose-based configuration and to image-metadata `remoteUser`. Task 1's tests
and Task 9's check confirm it; if either fails, the plan returns to revise mode
before Task 5.

## Implementation Steps

### Task 1: Give the Dev Container image an agent account with an empty home

**Files:** Modify: `docker/devcontainer/agentdev-devcontainer.Dockerfile`,
`scripts/tests/test_agentdev_devcontainer_image.py`,
`py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py`,
`scripts/tests/test_agentdev_devcontainer_lifecycle.py`

- [x] The image removes the stock `ubuntu` account and creates group and account
  `agent` (1000:1000, shell `/bin/bash`, home `/home/agent`), and creates
  `/home/agent` as an empty directory owned by `agent`.
  - **Evidence:**
    `scripts/tests/test_agentdev_devcontainer_image.py::test_the_image_gives_the_agent_account_an_empty_home_and_a_home_volume`
- [x] The image environment sets `AGENTDEV_USER=agent`,
  `AGENTDEV_HOME=/home/agent`,
  `AGENTDEV_AGENTS_AUTH_DIR=/var/lib/agentdev/auth`,
  `CLAUDE_SECURESTORAGE_CONFIG_DIR=/var/lib/agentdev/auth/claude`,
  `AGENTDEV_VENV_ROOT=/home/agent/.local/share/uv/venvs`, and
  `/home/agent/.local/bin` on `PATH`; no default names `/root` or `/uv`.
  - **Evidence:**
    `docker/devcontainer/agentdev-devcontainer.Dockerfile › "AGENTDEV_VENV_ROOT=/home/agent/.local/share/uv/venvs"`,
    `› "AGENTDEV_AGENTS_AUTH_DIR=/var/lib/agentdev/auth"`, and
    `› "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/agent/.local/bin"`
- [x] `devcontainer.metadata` adds `"remoteUser": "agent"`,
  `"updateRemoteUserUID": true`, and a volume `agentdev-home-${devcontainerId}`
  at `/home/agent`.
  - **Evidence:**
    `scripts/tests/test_agentdev_devcontainer_image.py::test_the_image_gives_the_agent_account_an_empty_home_and_a_home_volume`
- [x] Image tests assert `/home/agent` in the image is empty and owned by
  `agent`, the metadata carries the three entries, and `devcontainer up`, run on
  a Linux host by a non-1000 UID that owns the checkout, runs `id -u` in the
  container as that UID with an empty home owned by it.
  - **Evidence:**
    `scripts/tests/test_agentdev_devcontainer_image.py::test_the_image_gives_the_agent_account_an_empty_home_and_a_home_volume`
    and
    `scripts/tests/test_agentdev_devcontainer_image.py::test_the_agent_account_is_remapped_to_the_host_user_who_owns_the_checkout`,
    run by a host UID other than 0 and 1000
- [x] An image test opens a direct consumer that sets no `AGENTDEV_VENV_ROOT`
  and asserts its checkout's `.venv` links to a directory under
  `/home/agent/.local/share/uv/venvs`.
  - **Evidence:**
    `scripts/tests/test_agentdev_devcontainer_image.py::test_a_direct_consumer_gets_the_managed_runtime_without_lifecycle_scripts`,
    run by a host UID other than 0 and 1000;
    `scripts/tests/test_agentdev_devcontainer_lifecycle.py::test_create_makes_an_environment_root_inside_the_home`
    and
    `scripts/tests/test_agentdev_devcontainer_lifecycle.py::test_create_leaves_an_environment_root_outside_the_home_alone`

### Task 2: Move the base image's shell setup out of root's home

**Files:** Modify: `ansible/roles/bash_setup/tasks/main.yml`,
`ansible/roles/bun_setup/tasks/main.yml`, their `defaults/main.yml`,
`docker/base/agentdev-base.Dockerfile`,
`scripts/tests/test_agentdev_devcontainer_image.py`

- [x] Each role's managed bash and fish blocks take their target file from a
  role variable that defaults to the current `{{ user_home }}` path, so host
  provisioning is unchanged.
  - **Evidence:**
    `ansible/roles/bash_setup/defaults/main.yml#bash_setup_bashrc`,
    `ansible/roles/bun_setup/defaults/main.yml#bun_setup_bashrc` and
    `#bun_setup_fish_config`;
    `uv run ansible-lint ansible/roles/bash_setup ansible/roles/bun_setup`
- [x] The base image build points those variables at `/etc/bash.bashrc` and
  `/etc/fish/conf.d/`, and an interactive shell of an account with an empty home
  has `~/.local/bin` and `bun` on `PATH`.
  - **Evidence:**
    `scripts/tests/test_agentdev_devcontainer_image.py::test_an_interactive_shell_on_an_empty_home_gets_the_image_shell_setup`,
    against a Dev Container image built on a base image carrying the change

### Task 3: Bootstrap the Dev Container profile's instance storage

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py`,
`scripts/tests/test_agent_runtime_identity.py`

- [x] `agentdev-runtime bootstrap` in the Dev Container profile, for a non-root
  account read from `passwd`, claims the home mount root when it is empty and
  refuses when another identity owns a populated one, writes the sudoers entry,
  takes the shared-auth lock and initializes an empty auth volume, and checks
  the workspace is writable, naming the UID it must be writable by on refusal.
  - **Evidence:**
    `scripts/tests/test_agent_runtime_identity.py::test_a_non_root_devcontainer_claims_its_home_and_shared_auth`,
    `scripts/tests/test_agent_runtime_identity.py::test_a_non_root_devcontainer_creates_shared_auth_when_none_is_mounted`,
    `scripts/tests/test_agent_runtime_identity.py::test_a_non_root_devcontainer_refuses_a_home_another_identity_populated`,
    `scripts/tests/test_agent_runtime_identity.py::test_a_non_root_devcontainer_names_the_uid_an_unwritable_checkout_needs`
- [x] A root account keeps the root Dev Container bootstrap (account and mounts
  accepted as given, no home claim or sudoers entry), so a consumer overriding
  `AGENTDEV_USER=root` still starts.
  - **Evidence:**
    `scripts/tests/test_agent_runtime_identity.py::test_a_devcontainer_accepts_the_tools_account_and_workspace`

### Task 4: Store ~/.claude.json as a file on the home volume

**Files:** Modify:
`py_packages/agentdev_runtime/agentdev_runtime/claude_state.py`,
`py_packages/agentdev_runtime/agentdev_runtime/agent_state.py`,
`py_packages/agentdev_runtime/agentdev_runtime/doctor.py`,
`py_packages/agentdev_runtime/tests/test_claude_state.py`,
`py_packages/agentdev_runtime/tests/test_cbm_purge.py`,
`scripts/tests/test_agent_runtime_state.py`,
`scripts/tests/test_environment_health.py`

- [x] `agentdev-runtime state create` no longer links `~/.claude.json`. A home
  where it is a symlink to `~/.claude/claude.json` has the link replaced by a
  regular file with the target's content, and the target removed.
  - **Evidence:**
    `scripts/tests/test_agent_runtime_state.py::test_create_replaces_the_claude_json_link_with_its_target`,
    `scripts/tests/test_agent_runtime_state.py::test_create_keeps_a_regular_claude_json_and_links_nothing`,
    `scripts/tests/test_agent_runtime_state.py::test_create_leaves_a_link_elsewhere_alone`,
    `scripts/tests/test_environment_health.py::test_deploy_mode_redacts_auth_output`
- [x] `cbm_purge.purge` runs after that replacement, so a deploy home holding a
  codebase-memory-mcp entry behind the link loses the entry from the regular
  file, and a test runs that case.
  - **Evidence:**
    `py_packages/agentdev_runtime/tests/test_cbm_purge.py::test_create_purges_a_cbm_entry_once_the_claude_json_link_is_a_file`

### Task 5: Re-own the sibling checkout volume once

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py`,
`scripts/tests/test_agentdev_devcontainer_lifecycle.py`

- [x] `agentdev-runtime lifecycle created`, for a non-root account, re-owns
  `/workspaces/project` recursively when it is a mount owned by another UID, and
  leaves it untouched when the account already owns it.
  - **Evidence:**
    `scripts/tests/test_agentdev_devcontainer_lifecycle.py::test_create_re_owns_a_sibling_checkout_volume_another_uid_owns`,
    `scripts/tests/test_agentdev_devcontainer_lifecycle.py::test_create_leaves_a_sibling_checkout_the_account_owns_untouched`,
    `scripts/tests/test_agentdev_devcontainer_lifecycle.py::test_create_never_re_owns_the_open_workspace`

### Task 5a: Run the create phase under the supervisor after the bootstrap

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py`,
`py_packages/agentdev_runtime/agentdev_runtime/supervisor.py`,
`docker/devcontainer/supervisord.conf`,
`docker/devcontainer/agentdev-devcontainer.Dockerfile`,
`scripts/tests/test_agentdev_devcontainer_lifecycle.py`,
`scripts/tests/test_agent_runtime_profiles.py`

- [x] The Dev Container profile's `created` service runs
  `agentdev-runtime lifecycle created` after `keyring`, is core, and is never
  left out; readiness waits for it.
  - **Evidence:**
    `scripts/tests/test_agent_runtime_profiles.py::test_devcontainer_requires_its_persistent_services_and_the_create_phase`,
    `scripts/tests/test_agent_runtime_profiles.py::test_the_create_phase_gates_readiness_and_its_clients`,
    `scripts/tests/test_agent_runtime_profiles.py::test_the_profiles_share_their_program_definitions`
- [x] `agentdev-runtime lifecycle created` runs once per container and from the
  workspace folder; `created --wait` fails when the runtime fails first or the
  ready timeout passes.
  - **Evidence:**
    `scripts/tests/test_agentdev_devcontainer_lifecycle.py::test_create_runs_once_per_container`,
    `scripts/tests/test_agentdev_devcontainer_lifecycle.py::test_create_runs_its_hooks_from_the_workspace`,
    `scripts/tests/test_agentdev_devcontainer_lifecycle.py::test_wait_fails_when_the_runtime_fails_before_the_create_phase`,
    `scripts/tests/test_agentdev_devcontainer_lifecycle.py::test_wait_gives_up_after_the_ready_timeout`
- [x] The image label's `postCreateCommand` is
  `agentdev-runtime lifecycle created --wait`, and it sets
  `DEV_WORKSPACE_FOLDER` through `containerEnv`.
  - **Evidence:** `docker/devcontainer/agentdev-devcontainer.Dockerfile` ›
    `"postCreateCommand": "agentdev-runtime lifecycle created --wait"`;
    `scripts/tests/test_agentdev_devcontainer_image.py::test_a_direct_consumer_runs_each_phase_exactly_when_specified`

### Task 5b: Run the tests that need root from the runtime account

**Files:** Create: `scripts/run-root-tests`,
`scripts/tests/test_root_tests_launcher.py`; Modify:
`scripts/tests/conftest.py`, `scripts/tests/scratch.py`, `pyproject.toml`,
`.github/workflows/ci.yml`, `scripts/tests/test_cloud_startup.py`, and the
`requires_root` tests in `scripts/tests/test_agent_runtime_supervision.py`,
`scripts/tests/test_agent_runtime_profiles.py`,
`scripts/tests/test_agent_runtime_ingress.py`, and
`scripts/tests/test_agent_runtime_identity.py`

- [x] Tests marked `requires_root` skip in a run that is not root; under
  `scripts/run-root-tests`, a root run that selects an unmarked test is refused,
  and the launcher refuses to start as root.
  - **Evidence:**
    `scripts/tests/test_root_tests_launcher.py::test_a_marked_test_skips_without_root`,
    `scripts/tests/test_root_tests_launcher.py::test_the_launcher_guard_rejects_an_unmarked_test`,
    `scripts/tests/test_root_tests_launcher.py::test_root_without_the_launcher_runs_any_test`,
    `scripts/tests/test_root_tests_launcher.py::test_the_launcher_refuses_to_run_as_root`
- [x] `startup.py resume` tests keep the daemon pid files in scratch, never the
  host's `/var/run`.
  - **Evidence:**
    `scripts/tests/test_cloud_startup.py::test_resume_on_a_cloud_host_starts_docker`
- [x] As `agent` in a rebuilt Dev Container, the suite passes with the
  `requires_root` tests skipped; `scripts/run-root-tests` then runs them as
  root, they pass, and the run leaves no root-owned file in the checkout or
  `/tmp/agentdev-tests`.
  - **Evidence:** CI's `Devcontainer image (amd64)` and
    `Devcontainer image (arm64)` jobs on PR #800, whose step
    `.github/workflows/ci.yml` › "scripts/run-root-tests -n 8 scripts/tests"
    runs the suite as `agent`, then the launcher, then the leftover check:
    https://github.com/plume-works/agent-devcontainer/actions/runs/42924974146/job/130212190262
    and
    https://github.com/plume-works/agent-devcontainer/actions/runs/42924974146/job/130212190279

### Task 6: Point this repository's descriptor at the home volume

**Files:** Modify: `.devcontainer/devcontainer.json`,
`.devcontainer/docker-compose.yml`, `.devcontainer/devcontainer-init.sh`,
`scripts/tests/test_agentdev_devcontainer_repository.py`,
`py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py`,
`scripts/tests/test_agentdev_devcontainer_lifecycle.py`,
`.pre-commit-config.yaml`; Create: `scripts/tests/test_devcontainer_init.py`

- [x] `devcontainer.json` drops the `agentdev-claude`, `agentdev-opencode`,
  `agentdev-uv`, and `agentdev-pre-commit` mounts, and the
  `CLAUDE_SECURESTORAGE_CONFIG_DIR`, `PRE_COMMIT_HOME`, `UV_CACHE_DIR`, and
  `UV_PYTHON_INSTALL_DIR` overrides, so uv's cache and Python installs and
  pre-commit use their defaults under the home. `AGENTDEV_VENV_ROOT` is
  `/home/agent/.local/share/uv/venvs`, and no `UV_PROJECT_ENVIRONMENT` is set.
  `agentdev-project` stays.
  - **Evidence:**
    `.devcontainer/devcontainer.json › "AGENTDEV_VENV_ROOT": "/home/agent/.local/share/uv/venvs"`
    and `.devcontainer/devcontainer.json#mounts`, whose only entry is
    `agentdev-project`
- [x] `devcontainer-init.sh` creates `agentdev-agents-auth-<uid>-<gid>` from the
  host user's `id -u` and `id -g` and writes its name to `.env`, and
  `docker-compose.yml` mounts it at `/var/lib/agentdev/auth`.
  - **Evidence:**
    `scripts/tests/test_devcontainer_init.py::test_the_auth_volume_is_named_after_the_host_users_uid_and_gid`
    and `.devcontainer/docker-compose.yml#volumes.agentdev-agents-auth.name`
- [x] No mount target or environment value in `.devcontainer/` names `/root`.
  - **Evidence:**
    `! grep -rn /root .devcontainer/devcontainer.json .devcontainer/docker-compose.yml .devcontainer/devcontainer-init.sh`
- [x] `agentdev-runtime lifecycle created` no longer claims a `/uv` mount, and
  the `link-venv` hook's name in `.pre-commit-config.yaml` no longer names
  `/uv/venvs`.
  - **Evidence:**
    `! grep -n /uv py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py .pre-commit-config.yaml`;
    `py_packages/agentdev_runtime/tests/test_worktree_register.py::test_the_create_phase_registers_the_hooks_outside_deploy_mode`

### Task 7: Move the deploy runtime's uv state onto its home volume

**Files:** Modify: `compose.opencode.yml`,
`docker/deploy/agentdev-deploy.Dockerfile`,
`py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py`,
`py_packages/agentdev_runtime/agentdev_runtime/settings.py`,
`py_packages/agentdev_runtime/README.md`, `README.md`,
`scripts/tests/test_agent_runtime_compose.py`,
`scripts/tests/test_agent_runtime_identity.py`,
`scripts/tests/test_agent_runtime_acceptance.py`

- [x] `compose.opencode.yml` mounts no `/uv` volume and declares none.
  - **Evidence:**
    `scripts/tests/test_agent_runtime_compose.py::test_clone_deployment_uses_project_volumes_and_the_shared_auth_volume`
- [x] The deploy image drops `UV_CACHE_DIR` and `UV_PYTHON_INSTALL_DIR`, and
  sets `UV_PROJECT_ENVIRONMENT=/home/agent/.local/share/uv/venvs/project`.
  - **Evidence:**
    `scripts/tests/test_agent_runtime_acceptance.py::test_clone_start_prepares_a_python_project_with_pre_commit`
    and
    `scripts/tests/test_agent_runtime_acceptance.py::test_a_failed_uv_sync_degrades_while_opencode_serves_until_retried`,
    with `AGENTDEV_RUNTIME_TEST_IMAGE` set to a deploy image built from this
    tree
- [x] The deploy bootstrap no longer requires or claims a `/uv` mount; the
  compose test's instance targets are `/home/agent` and `/var/lib/docker`.
  - **Evidence:**
    `scripts/tests/test_agent_runtime_identity.py::test_creates_the_account_and_claims_fresh_instance_storage`
    and `scripts/tests/test_agent_runtime_compose.py::INSTANCE_TARGETS`

### Task 8: Migrate template consumers

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/project.py`,
`py_packages/agentdev_runtime/tests/test_project_link_venv.py`, the
`template-consume` skill's update guidance under
`.agents/plugins/agentdev/skills/template-consume/` (`SKILL.md` and
`references/consumption-guide.md`),
`scripts/tests/test_template_consume_migration.py`

- [x] An update from a pre-change template removes the per-directory state
  mounts and `/root` paths from the consumer's descriptor and states that agent
  state and logins reset once.
  - **Evidence:**
    `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md#migrating-to-the-home-volume`,
    `.agents/plugins/agentdev/skills/template-consume/SKILL.md#update-mode › "Migrating to the home volume"`,
    and
    `scripts/tests/test_template_consume_migration.py::test_a_migrated_consumer_reaches_runtime_readiness`,
    run by a host UID other than 0 and 1000
- [x] A checkout opened in the pre-change Dev Container keeps a `.venv` link
  into the removed `/uv` volume; the next project sync replaces that dangling
  link with one to the checkout's environment on the home volume, and still
  leaves a live link elsewhere alone.
  - **Evidence:**
    `py_packages/agentdev_runtime/tests/test_project_link_venv.py::test_a_dangling_link_outside_the_root_is_replaced`,
    `py_packages/agentdev_runtime/tests/test_project_link_venv.py::test_a_foreign_link_is_left_with_a_warning`

### Task 9: Accept a rebuilt Dev Container on a host-owned checkout

**Files:** none (a Linux host whose checkout is owned by the host user)

- [x] A rebuilt Dev Container runs as `agent` with the host user's UID and GID.
  - **Evidence:** in the repository owner's Coder workspace `home-volume-test`
    (coder-ide-baseline `main-98f4ce0`, PR #800's candidate image
    `sha-58cfdc4`), `id` in the container reports `agent` 1000:1000, matching
    the host user `coder` 1000:1000, and the checkout and `/home/agent` are
    owned by `agent`.
- [x] After `docker restart`, the supervisor reports its required services
  ready.
  - **Evidence:** in that workspace, `agentdev-runtime health ready` exits 0
    after `docker restart`, and the container log reads
    `agentdev-runtime: all services are ready`.
- [x] `agentdev:*` skills resolve in Claude Code.
  - **Evidence:** in that workspace, `claude plugin list` shows
    `agentdev@agent-devcontainer` enabled, and `claude -p` lists the
    `agentdev:*` skills.
- [x] Claude stays logged in across a second rebuild.
  - **Evidence:** after the repository owner logged in,
    `devcontainer up --remove-existing-container` replaced the container, and
    `claude auth status` still reports `loggedIn: true`.
- [x] `git-new-branch --worktree` from the checkout creates its worktree as
  `agent`.
  - **Evidence:** in that workspace, `git-new-branch.py <name> --worktree`
    returned `RESULT=SUCCESS`, and every file in the new worktree is owned by
    `agent`.

### Task 10: Record the shipped model

**Files:** Modify:
`docs/knowledge/data/architecture/devcontainer-home-volume.md`,
`docs/knowledge/data/architecture/agent-auth-persistence.md`,
`docs/knowledge/data/features/persist-pre-commit-cache.md`,
`docs/knowledge/data/architecture/uv-environment-location.md`

- [x] The architecture document describes the shipped account and volumes; the
  auth document and the pre-commit feature name the home volume and the cohort
  auth volume instead of the per-directory volumes.
  - **Evidence:**
    `docs/knowledge/data/architecture/devcontainer-home-volume.md#the-account-and-its-volumes`,
    `docs/knowledge/data/architecture/agent-auth-persistence.md#decision`, and
    `docs/knowledge/data/features/persist-pre-commit-cache.md#behaviour`
- [x] The uv environment location document places the uv cache and every
  checkout's environment on the home volume instead of the `/uv` volume.
  - **Evidence:**
    `docs/knowledge/data/architecture/uv-environment-location.md#why-the-environment-is-out-of-tree`

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
`agentdev-devcontainer`'s create phase SHALL also install it into the
runtime account's home volume, which starts empty and receives no image
content. `~/.claude.json` SHALL be a regular file on that volume.

#### Scenario: the image runs with no volumes and no lifecycle hooks

- **WHEN** a container starts from `agentdev-base` without client-state volumes
  and no lifecycle command runs
- **THEN** the catalog installed during the image build is present, an
  `agentdev:*` skill resolves in Claude Code, and OpenCode loads the
  staged bridge plugin and lists the catalog's skills.

#### Scenario: a devcontainer starts for the first time on a fresh home volume

- **WHEN** the create phase runs, `$AGENTDEV_CATALOG_DIR` exists, and the
  home volume is empty
- **THEN** the staged catalog is installed at Claude user scope and
  into the OpenCode user config on the home volume, and `~/.claude.json` is a
  regular file holding no image content.

#### Scenario: a devcontainer starts with a catalog already installed on its home volume

- **WHEN** the home volume already holds a prior install and `~/.claude.json`,
  and the container is recreated
- **THEN** `~/.claude.json`'s content is preserved (Claude may append bootstrap
  fields, so the guarantee is content preservation, not byte-identity), and the create phase re-applies the
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
decision is [No code-graph index](../architecture/no-code-graph.md).

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
with its home on one per-instance volume. Its create phase SHALL run under the
supervisor after the root bootstrap, once per container, and gate readiness;
`postCreateCommand` SHALL wait for it and fail when the runtime fails first.

``` markdown
## MODIFIED Requirements

### Requirement: each checkout has its own project environment

The Dev Container SHALL give every checkout of the workspace repository,
including each Git worktree, its own uv project environment: `.venv` in the
checkout SHALL be a link to a directory named after the checkout under
`AGENTDEV_VENV_ROOT` (`/home/agent/.local/share/uv/venvs` in
`agentdev-devcontainer`, else `/uv/venvs`), on the same volume as the uv cache.
The create phase SHALL register `agentdev-runtime worktree create` and
`agentdev-runtime worktree remove` as the user's Claude `WorktreeCreate` and
`WorktreeRemove` hooks. The link SHALL exist before a worktree's first command
when the worktree is made by `git worktree add` or by that `WorktreeCreate`
hook, and the attach phase SHALL create it for the workspace folder. The
`WorktreeRemove` hook SHALL delete the environment of the worktree it removes;
attach SHALL keep every environment named after a listed checkout or linked from
the `.venv` of any checkout, in any repository, and remove the rest.

#### Scenario: two worktrees run uv at once

- **WHEN** two worktrees with different versions of the project's packages run
  `uv run` concurrently
- **THEN** each imports its own checkout's packages, and neither sync changes
  the other's environment

#### Scenario: an agent creates a worktree

- **WHEN** a Claude Code session or a worktree-isolated subagent starts in a new
  worktree
- **THEN** the worktree is at `.claude/worktrees/<name>` on branch
  `worktree-<name>`, and its `.venv` links to its own environment before the
  session starts

#### Scenario: a worktree name is used again

- **WHEN** `WorktreeCreate` fires with a name used before, such as a session
  Remote Control revives
- **THEN** the hook reuses that name's worktree, or checks out its kept
  `worktree-<name>` branch when the worktree was removed, and prints its path

#### Scenario: Claude Code removes a worktree

- **WHEN** Claude Code removes a worktree its `WorktreeCreate` hook made
- **THEN** that worktree's environment directory is deleted at once, and its
  `worktree-<name>` branch is kept

#### Scenario: a worktree is removed outside Claude Code

- **WHEN** a worktree is removed with `git worktree remove` and the workspace is
  next attached
- **THEN** its environment directory is deleted, and no environment a checkout
  of any repository still links to is touched

#### Scenario: a consumer sets no environment root

- **WHEN** a consumer of `agentdev-devcontainer` that sets no
  `AGENTDEV_VENV_ROOT` attaches to a Python checkout
- **THEN** the checkout's `.venv` links to its directory under
  `/home/agent/.local/share/uv/venvs`, on the home volume that holds uv's cache
```

## Depends on

[Replace the runtime shell scripts with one agentdev-runtime
CLI](20261029-off-bash-migration.md)

[Narrow the image build context](20261102-narrow-image-build-context.md)

[Give each checkout its own uv
environment](20261101-per-checkout-uv-environments.md)

## Verification

- `uv run pytest scripts/tests/test_agentdev_devcontainer_image.py scripts/tests/test_agent_runtime_identity.py scripts/tests/test_agentdev_devcontainer_lifecycle.py scripts/tests/test_template_consume_migration.py`
  and the `agentdev_runtime` package tests pass.
- In a rebuilt Dev Container: `id` reports `agent` with the host UID;
  `findmnt /home/agent` shows the home volume; `findmnt` shows no mount below
  `/root` and none below the workspace except `agentdev-project`;
  `test -f ~/.claude.json && ! test -L ~/.claude.json`; `readlink .venv` in the
  workspace names a directory under `/home/agent/.local/share/uv/venvs`.
- `docker restart` of the container ends with
  `agentdev-runtime: all services are ready`.
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
- Root hosts: `devcontainer up` run by root leaves `agent` at 1000:1000, and the
  bootstrap refuses the root-owned checkout. They are unsupported (see the
  architecture document's constraints).

## Key references

- `docker/devcontainer/agentdev-devcontainer.Dockerfile › "AGENTDEV_USER=agent"`
  — `AGENTDEV_USER`
- `docker/devcontainer/agentdev-devcontainer.Dockerfile › "AGENTDEV_HOME=/home/agent"`
  — `AGENTDEV_HOME`
- `docker/devcontainer/agentdev-devcontainer.Dockerfile › "LABEL devcontainer.metadata="`
  — `devcontainer.metadata`
- `docker/deploy/agentdev-deploy.Dockerfile › "RUN userdel --remove ubuntu"` —
  `userdel --remove ubuntu`
- `docker/deploy/agentdev-deploy.Dockerfile › "UV_PROJECT_ENVIRONMENT=/home/agent/.local/share/uv/venvs/project"`
  — the deploy project venv
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
- `py_packages/agentdev_runtime/agentdev_runtime/agent_state.py::unlink_claude_json`
  — `unlink_claude_json`
- `py_packages/agentdev_runtime/agentdev_runtime/agent_state.py::create` —
  `create`
- `py_packages/agentdev_runtime/agentdev_runtime/agent_state.py::create` —
  `cbm_purge.purge`
- `py_packages/agentdev_runtime/agentdev_runtime/settings.py::VARIABLES` —
  `AGENTDEV_CLAUDE_JSON`
- `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py::claim_project` —
  `claim_project`
- `py_packages/agentdev_runtime/agentdev_runtime/project.py::link_venv` —
  creates the `.venv` link under `AGENTDEV_VENV_ROOT`
- `py_packages/agentdev_runtime/agentdev_runtime/settings.py::VARIABLES` —
  `AGENTDEV_VENV_ROOT`, default `/uv/venvs`
- `.pre-commit-config.yaml › "link .venv to its own uv environment"` — the
  `link-venv` hook's name
- `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py::created` —
  `created`
- `docker/devcontainer/supervisord.conf › "user=%(ENV_AGENTDEV_USER)s"` —
  `user=%(ENV_AGENTDEV_USER)s`
- `.devcontainer/devcontainer.json › "AGENTDEV_VENV_ROOT"` —
  `AGENTDEV_VENV_ROOT`
- `.devcontainer/devcontainer.json › "agentdev-project"` — `agentdev-project`
  mount
- `.devcontainer/docker-compose.yml#volumes.agentdev-agents-auth.external` —
  `agentdev-agents-auth` mount
- `.devcontainer/devcontainer-init.sh › "docker volume create \"$auth_volume\""`
  — the cohort auth volume
- `compose.opencode.yml › "home:/home/agent"` — the deploy home volume
- `scripts/tests/test_agent_runtime_compose.py::INSTANCE_TARGETS` —
  `INSTANCE_TARGETS`
- `ansible/roles/bash_setup/defaults/main.yml#bash_setup_bashrc` — `.bashrc`
  target
- `ansible/roles/bun_setup/defaults/main.yml#bun_setup_bashrc` — `.bashrc`
  target
