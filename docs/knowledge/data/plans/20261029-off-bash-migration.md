---
type: plan
created: 2026-10-29
release:
- features/agentdev-runtime-cli
- bugs/workspace-image-lacks-hook-binaries
description: Replace the runtime's shell scripts, the Xpra launcher, the firewall script, and two publisher scripts with one agentdev-runtime Python CLI packaged as an embedded uv tool in the runtime images, and remove the Codex Cloud bootstrap.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T16:18:33Z
sources:
- resource: .devcontainer/scripts/
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: docker/devcontainer/supervisord.conf
- resource: docker/deploy/supervisord.conf
- resource: ansible/roles/validate_agent_files/tasks/main.yml
- resource: ansible/roles/devcontainer_firewall/files/init-firewall.sh
- resource: docker/desktop/start-xpra.sh
- resource: .github/actions/run-claude-responder/action.yml
- resource: docs/knowledge/data/architecture/ci-agent-plugin-availability.md
- resource: docs/knowledge/data/plans/20260905-python-skill-scripts.md
- resource: docs/knowledge/data/bugs/workspace-image-lacks-hook-binaries.md
- resource: .pre-commit-config.yaml
- resource: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idcontaineroptions
- resource: https://github.com/anthropics/claude-code-action/blob/v1/action.yml
---

# Replace the runtime shell scripts with one agentdev-runtime CLI

## Context

[agentdev-runtime CLI](../features/agentdev-runtime-cli.md) is the feature this
plan implements. [Publish the reusable agentdev Dev Container
image](20261023-reusable-agentdev-devcontainer.md) moved the lifecycle into the
`agentdev-devcontainer` and `agentdev-deploy` images and sealed it under
`/opt/agentdev-runtime`; consumers no longer copy `.devcontainer/scripts/`. The
constraint that kept those scripts shell, a template artifact that had to run on
a stock image, no longer binds the runtime. [Python skill
scripts](20260905-python-skill-scripts.md) recorded that constraint and the rule
that inline Python inside bash is neither testable nor lintable.

The runtime is 41 shell scripts (2647 lines) beside a 1133-line Python
supervisor. The scripts read 54 distinct `AGENTDEV_*` settings against the
supervisor's 23, each file declaring its own defaults, and one variable defaults
to two different paths in two files. The supervisor writes `state.json` in
Python and `runtime-health.sh` parses it back with jq. Fourteen scripts are
subcommand dispatchers, and thirteen call one another through
`$script_dir/<name>.sh`, with the environment as the parameter list. Three
scripts run under `uv run --script` and resolve `tomlkit` and `json5` from PyPI
the first time they run, inside the deploy profile's core `prepare` phase. A
second, no-supervisor start path for GitHub `container:` jobs and Codex Cloud
keeps `setup-keyring.sh`, `codebase-memory-mcp-start.sh`, and `firewall.sh`
alive beside their supervised twins ([CI agent plugin
availability](../architecture/ci-agent-plugin-availability.md)). The Codex Cloud
bootstrap is removed at the user's decision.

The user's decisions for this plan: one Python package installed as a uv tool
the way `validate_agent_files` is; one CLI rather than per-script shims; the
catalog's scripts in their own plan, [Port the catalog's bundled shell scripts
to Python](20261029-catalog-scripts-python.md); a CBM-only start when no
supervisor is present, with the legacy no-supervisor starters deleted; the
firewall script ported rather than wrapped; and the detection that [Bug: a
workspace on a pre-pin image has no gitleaks or actionlint and nothing says
so](../bugs/workspace-image-lacks-hook-binaries.md) asks for, carried by
`doctor` and `project hooks` as this plan's one behaviour change.

Three other open bugs sit in scripts this plan ports. [Bug: the Remote Control
watcher restarts a session that never comes up on every
tick](../bugs/remote-control-watcher-start-loop.md) is fixed in shell before
Task 10, so the port's baseline carries the fix. [Bug: a CBM daemon start
failure latches the standalone runtime
degraded](../bugs/cbm-start-failure-latches-degraded.md) and [Bug: Codex login
stops being shared between standalone
projects](../bugs/standalone-codex-auth-unshared.md) have no settled root cause
and are fixed after the port, in the package.

## Approach

One package, `py_packages/agentdev_runtime/`, with its own `pyproject.toml`,
test suite, and one console script, `agentdev-runtime`. Both runtime Dockerfiles
install it with `uv tool install` from the bind-mounted build context onto the
system interpreter, into `/opt/uv-tools` with the entry point on
`/usr/local/bin`, no cache and no interpreter download, mirroring the validator
role. The package pins `supervisor`, `tomlkit`, `json5`, `pyyaml`, and
`setuptools<85`; the apt `supervisor` package leaves both images.
`agentdev-base` stays lifecycle-neutral and never carries the package.

Every script becomes a subcommand of one CLI whose nouns are the runtime's
concerns. One settings module parses every environment value once, with one
default per variable, keyed by profile where the scripts disagree today. One
state module defines the `state.json`, retry, and failure-record shapes for
writer and reader alike. Behaviour behind each command is unchanged; this plan
changes language and packaging, not policy, so every existing scenario in the
affected specs holds as written.

The one exception is the hook-binary detection. After registering the hooks,
`project hooks` warns about each `language: system` hook in the checkout's
`.pre-commit-config.yaml` whose `entry` executable is not on `PATH`, and
`doctor` requires `gitleaks` and `actionlint` in its toolchain section. A
missing hook executable is a warning, not a failure, in both profiles, so a
consumer whose own hooks need tools the image lacks still starts; reading the
hook configuration is why the package needs `pyyaml`.

The migration is incremental. The package installs beside the scripts first, PID
1 and the healthcheck switch to the CLI next, and each service then moves with
its supervisord `command=` and its tests, so the image boots at every task
boundary. The last runtime task removes the `COPY` of the script tree and the
sha256 manifest; integrity moves to the installed distribution's `RECORD`
hashes, which keeps the derived-image protection the manifest provided.

A container with no supervisor socket runs `lifecycle ready --no-wait`, one
function that starts the CBM daemon and then the per-start repairs. Nothing else
starts there: a review job needs CBM and the checkout catalog and never the
keyring, firewall, or a desktop. A GitHub `container:` job runs no image
entrypoint and accepts no `--entrypoint` option, and `claude-code-action` is a
composite action that runs in the job's own runtime, so the supervisor can never
be PID 1 there; this function is the supported start for such a job.

The firewall and the Xpra launcher join the package. The firewall runs as root
from the bootstrap in both profiles, so its sudoers entry and the script in the
Ansible role go; the role keeps the packages. The devcontainer profile reads the
checkout's allowlist when present, as `spec/firewall` promises, and the image
copy otherwise, as the supervised wrapper does; deploy keeps the image copy.

Rejected: loose stdlib scripts on the system interpreter, which keeps either the
runtime PyPI fetch or an apt dependency hunt and keeps the file manifest; bash
shims preserving the `/opt/agentdev-runtime/*.sh` names, which the user ruled
out in favour of one CLI; porting the legacy no-supervisor starters, which would
preserve a second start path nobody needs; keeping `init-firewall.sh` as bash
behind a Python wrapper, which the user ruled out; starting the supervisor as a
background process inside the responder's container job, which needs a
privileged job container for the profile's core `dockerd` and buys only the
deletion of this one function; and running the responder as a host job through
`devcontainers/ci`, which gives the supervisor PID 1 but loses
`claude-code-action` and its `claude[bot]` authentication.

## Implementation Steps

### Task 1: Install the package beside the scripts

**Files:** Create: `py_packages/agentdev_runtime/pyproject.toml`,
`py_packages/agentdev_runtime/README.md`,
`py_packages/agentdev_runtime/agentdev_runtime/__init__.py`,
`py_packages/agentdev_runtime/agentdev_runtime/cli.py`,
`py_packages/agentdev_runtime/agentdev_runtime/settings.py`,
`py_packages/agentdev_runtime/tests/test_settings.py`,
`py_packages/agentdev_runtime/tests/test_cli.py`; Modify: `pyproject.toml`,
`uv.lock`, `.dockerignore`, `docker/deploy/agentdev-deploy.Dockerfile`,
`docker/devcontainer/agentdev-devcontainer.Dockerfile`

- [ ] The package declares `requires-python >= 3.12`, the console script
  `agentdev-runtime`, and dependencies `supervisor` at the version the root
  project pins today, `setuptools<85`, `tomlkit`, `json5`, and `pyyaml`. The
  root project takes the package as an editable dev dependency and drops its
  direct `supervisor` and `setuptools` pins; `uv.lock` is regenerated.
- [ ] Both runtime Dockerfiles install the package with
  `uv tool install --reinstall --python /usr/bin/python3` from the bind-mounted
  build context, with `UV_TOOL_DIR=/opt/uv-tools`,
  `UV_TOOL_BIN_DIR=/usr/local/bin`, `UV_NO_CACHE=1`,
  `UV_PYTHON_DOWNLOADS=never`, and `UV_LINK_MODE=copy`. `.dockerignore` admits
  `py_packages/agentdev_runtime`. The `COPY .devcontainer/scripts/` lines stay
  until Task 13.
- [ ] `settings.py` parses every environment value the scripts and the
  supervisor read, with one default per variable, keyed by profile where the
  scripts disagree; the package README lists each variable, its default, and the
  profiles that read it.

### Task 2: Boot PID 1 and the healthcheck through the CLI

**Files:** Create:
`py_packages/agentdev_runtime/agentdev_runtime/supervisor.py`,
`py_packages/agentdev_runtime/agentdev_runtime/health.py`,
`py_packages/agentdev_runtime/agentdev_runtime/state.py`,
`py_packages/agentdev_runtime/tests/test_state.py`; Modify:
`docker/deploy/agentdev-deploy.Dockerfile`,
`docker/devcontainer/agentdev-devcontainer.Dockerfile`,
`docker/deploy/supervisord.conf`, `docker/devcontainer/supervisord.conf`,
`scripts/tests/test_agent_runtime_supervision.py`,
`scripts/tests/test_agent_runtime_profiles.py`,
`scripts/tests/test_agent_runtime_state.py`,
`scripts/tests/test_agent_runtime_ci.py`; Delete:
`.devcontainer/scripts/runtime-supervisor.py`,
`.devcontainer/scripts/runtime-health.sh`

- [ ] `runtime-supervisor.py` becomes
  `agentdev-runtime supervisor run|control|exec|retry` with its behaviour
  unchanged; the `state.json`, retry-request, and failure-record shapes live in
  `state.py` and are the only way the package reads or writes them.
- [ ] `runtime-health.sh` becomes
  `agentdev-runtime health <service>|ready|status`, reading state through
  `state.py`; user-scope probes still re-exec as the runtime user; probes call
  the service modules as they land and the remaining scripts until then.
- [ ] `ENTRYPOINT`, `HEALTHCHECK`, the controller listener, and every `command=`
  in both supervisord configurations name the CLI, and the `exec` wrapper keeps
  its output capture and failure record. Both images stop installing the apt
  `supervisor` package, which PID 1 needs until it runs from the CLI.

### Task 3: Bootstrap and distribution integrity

**Files:** Create: `py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py`,
`py_packages/agentdev_runtime/agentdev_runtime/integrity.py`,
`py_packages/agentdev_runtime/tests/test_integrity.py`; Modify:
`scripts/tests/test_agent_runtime_identity.py`,
`scripts/tests/test_agentdev_devcontainer_image.py`,
`docker/devcontainer/agentdev-devcontainer.Dockerfile`; Delete:
`.devcontainer/scripts/runtime-bootstrap.sh`

- [ ] `agentdev-runtime bootstrap` reproduces both profiles: identity validation
  and account reuse or creation, the sudoers entry through `visudo`,
  instance-storage claims that chown only an empty mount root, the shared-auth
  lock, the runtime-directory reset, and the docker group. Account and privilege
  changes stay subprocess calls to `groupadd`, `useradd`, `usermod`, `visudo`,
  and `setpriv`.
- [ ] `integrity.py` verifies the installed `agentdev_runtime` distribution
  against its `RECORD` hashes and file set before the bootstrap continues, and
  refuses with the same remedy the manifest check names today. The sha256
  manifest step leaves the Dockerfile, and the derived-image test patches a
  package file instead of a script.

### Task 4: Firewall

**Files:** Create: `py_packages/agentdev_runtime/agentdev_runtime/firewall.py`,
`py_packages/agentdev_runtime/tests/test_firewall_allowlist.py`; Modify:
`ansible/roles/devcontainer_firewall/tasks/main.yml`,
`scripts/tests/test_agent_runtime_firewall.py`; Delete:
`ansible/roles/devcontainer_firewall/files/init-firewall.sh`,
`ansible/roles/devcontainer_firewall/files/devcontainer-firewall-sudoers`,
`.devcontainer/scripts/runtime-firewall.sh`, `.devcontainer/scripts/firewall.sh`

- [ ] `agentdev-runtime firewall apply` reproduces `init-firewall.sh` and
  `runtime-firewall.sh`: the `ENABLE_FIREWALL` gate, allowlist validation,
  Docker DNS rule capture and restore, host SSH, loopback, the `allowed-domains`
  ipset from resolved A records and GitHub meta ranges collapsed with
  `ipaddress`, default DROP, established, allowlist accept, reject, the IPv6
  block, the `DOCKER-USER` chain, deploy proxy ingress, and the two
  self-verification requests. `iptables` and `ipset` run as argument lists
  through subprocess.
- [ ] The devcontainer profile reads
  `<workspace>/.devcontainer/firewall-allowlist.txt` when it exists and
  `/etc/agentdev/firewall-allowlist.txt` otherwise; deploy reads
  `FIREWALL_ALLOWLIST` or the image copy.
- [ ] The Ansible role keeps `iptables` and `ipset`, drops the script, the
  sudoers file, and any package only the script used once a repository grep
  confirms no other user.

### Task 5: Docker and keyring services

**Files:** Create: `py_packages/agentdev_runtime/agentdev_runtime/docker.py`,
`py_packages/agentdev_runtime/agentdev_runtime/keyring.py`; Modify:
`docker/deploy/supervisord.conf`, `docker/devcontainer/supervisord.conf`,
`scripts/tests/test_agent_runtime_docker.py`,
`scripts/tests/test_agent_runtime_keyring.py`,
`scripts/tests/test_docker_image_prune.py`; Delete:
`.devcontainer/scripts/runtime-docker.sh`,
`.devcontainer/scripts/docker-image-prune.sh`,
`.devcontainer/scripts/runtime-keyring.sh`,
`.devcontainer/scripts/setup-keyring.sh`

- [ ] `agentdev-runtime docker run` performs the privilege, storage, private
  endpoint, and single-engine preflights and then execs `dockerd`;
  `agentdev-runtime docker prune` keeps the 72-hour filter and warning-only
  failures.
- [ ] `agentdev-runtime keyring dbus|keyring|check|wait` execs `dbus-daemon` and
  `gnome-keyring-daemon` after the bus wait, creates the login keyring once and
  never overwrites it, and `setup-keyring.sh` is deleted without a replacement.

### Task 6: Xpra

**Files:** Create: `py_packages/agentdev_runtime/agentdev_runtime/xpra.py`;
Modify: `docker/deploy/supervisord.conf`,
`docker/devcontainer/supervisord.conf`, `docker/base/agentdev-base.Dockerfile`;
Delete: `docker/desktop/start-xpra.sh`

- [ ] `agentdev-runtime xpra --supervised|--background|--stop` with `--host`,
  `--port`, and `--display` reproduces the launcher: display normalisation and
  lock clearing, orphaned X server reclaim, GPU detection and VirtualGL setup,
  the password through the environment, signal cleanup, and `exec` in supervised
  mode. The base image stops copying `/start-xpra.sh`.

### Task 7: OpenCode and the Coder start

**Files:** Create: `py_packages/agentdev_runtime/agentdev_runtime/opencode.py`,
`py_packages/agentdev_runtime/agentdev_runtime/coder.py`; Modify:
`docker/deploy/supervisord.conf`, `docker/devcontainer/supervisord.conf`,
`scripts/tests/test_agent_runtime_ingress.py`,
`scripts/tests/test_opencode_web_start.py`,
`scripts/tests/test_coder_agent_start.py`,
`scripts/e2e/iwe-workflows/opencode_credential.py`; Delete:
`.devcontainer/scripts/opencode-web-command.sh`,
`.devcontainer/scripts/opencode-web-start.sh`,
`.devcontainer/scripts/coder-agent-start.sh`

- [ ] `agentdev-runtime opencode serve|probe|link|coder-start` keeps the
  password requirement, the 0600 generated password file, the Coder tmux
  session, and the authenticated `/api/info` probe.
- [ ] `agentdev-runtime coder start` runs prune, the credential helper, and the
  OpenCode start as warnings on failure, then execs the Remote Control start.

### Task 8: CBM

**Files:** Create: `py_packages/agentdev_runtime/agentdev_runtime/cbm.py`,
`py_packages/agentdev_runtime/agentdev_runtime/codex_hooks.py`,
`py_packages/agentdev_runtime/tests/test_codex_hooks.py`; Modify:
`docker/deploy/supervisord.conf`, `docker/devcontainer/supervisord.conf`,
`scripts/tests/test_agent_runtime_cbm.py`,
`scripts/tests/test_codebase_memory_mcp_index.py`,
`scripts/tests/test_repair_codex_cbm_hooks_block.py`; Delete:
`.devcontainer/scripts/runtime-cbm.sh`,
`.devcontainer/scripts/codebase-memory-mcp-install.sh`,
`.devcontainer/scripts/codebase-memory-mcp-index.sh`,
`.devcontainer/scripts/codebase-memory-mcp-start.sh`,
`.devcontainer/scripts/repair-codex-cbm-hooks-block.py`

- [ ] `agentdev-runtime cbm install|start|check|index <repo>|run|stop` keeps the
  daemon generation as PID plus `/proc` start time, the user-owned binary copy,
  the `~/.claude.json` materialise-and-restore as a context manager,
  `hooks.json` creation, the Codex hooks-block repair as a module, and the async
  index request with its acceptance check.

### Task 9: Agent state and catalog registration

**Files:** Create:
`py_packages/agentdev_runtime/agentdev_runtime/agent_state.py`,
`py_packages/agentdev_runtime/agentdev_runtime/catalog.py`,
`py_packages/agentdev_runtime/agentdev_runtime/codex_config.py`,
`py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py`,
`py_packages/agentdev_runtime/agentdev_runtime/claude_state.py`,
`py_packages/agentdev_runtime/tests/test_codex_config.py`,
`py_packages/agentdev_runtime/tests/test_opencode_config.py`,
`py_packages/agentdev_runtime/tests/test_claude_state.py`; Modify:
`scripts/tests/test_configure_codex.py`,
`scripts/tests/test_configure_opencode.py`,
`scripts/tests/test_preapprove_claude_workspace.py`,
`scripts/e2e/iwe-workflows/harness_codex.py`; Delete:
`.devcontainer/scripts/setup-agent-state.sh`,
`.devcontainer/scripts/runtime-paths.sh`,
`.devcontainer/scripts/link-codex-auth.sh`,
`.devcontainer/scripts/preapprove-claude-workspace.sh`,
`.devcontainer/scripts/configure-codex.py`,
`.devcontainer/scripts/configure-opencode.py`,
`.devcontainer/scripts/reinstall-agentdev-claude.sh`,
`.devcontainer/scripts/reinstall-agentdev-codex.sh`,
`.devcontainer/scripts/reinstall-agentdev-opencode.sh`

- [ ] `agentdev-runtime state create|links|agent-policy|cbm` runs under one
  configuration lock, keeps deploy's fatal and the devcontainer's nonfatal CBM
  install, the user-tool registration, the auth directories, the
  `~/.claude.json` link, the Codex `auth.json` link repair, and the Claude
  pre-approval with its skip variable.
- [ ] `agentdev-runtime catalog install <root> [--claude-scope user|local]`
  registers the Claude marketplace and plugins, the Codex marketplace with the
  already-registered short-circuit and the agents installer, and the OpenCode
  bridge entry; the complete-catalog test is one function in the package.

### Task 10: Remote Control

**Files:** Create:
`py_packages/agentdev_runtime/agentdev_runtime/remote_control.py`; Modify:
`docker/deploy/supervisord.conf`, `docker/devcontainer/supervisord.conf`,
`scripts/tests/test_runtime_remote_control.py`,
`scripts/tests/test_claude_remote_control_start.py`,
`scripts/tests/test_claude_remote_control_session.py`,
`scripts/tests/test_claude_remote_control_pin.py`; Delete:
`.devcontainer/scripts/runtime-remote-control.sh`,
`.devcontainer/scripts/claude-remote-control-start.sh`,
`.devcontainer/scripts/claude-remote-control-session.sh`,
`.devcontainer/scripts/claude-remote-control-pin.sh`

- [ ] `agentdev-runtime remote-control run|check|start|session [name]|pin` keeps
  the credential-signature watch, the mode and spawn validation, the
  `tmux -L claude-remote` server, the pinned-conversation resume, and the
  SessionStart hook, whose command in `--settings` becomes
  `agentdev-runtime remote-control pin`.

### Task 11: Workspace, project, and git helpers

**Files:** Create: `py_packages/agentdev_runtime/agentdev_runtime/workspace.py`,
`py_packages/agentdev_runtime/agentdev_runtime/project.py`,
`py_packages/agentdev_runtime/agentdev_runtime/git.py`,
`py_packages/agentdev_runtime/tests/test_project_hooks.py`; Modify:
`docker/deploy/supervisord.conf`,
`scripts/tests/test_agent_runtime_workspace.py`,
`scripts/tests/test_setup_gh_credential_helper.py`, `AGENTS.md`,
`.agents/plugins/agentdev/skills/microvm-sandbox/SKILL.md`; Delete:
`.devcontainer/scripts/runtime-workspace.sh`,
`.devcontainer/scripts/uv-sync.sh`, `.devcontainer/scripts/setup-pre-commit.sh`,
`.devcontainer/scripts/setup-git-safe-directory.sh`,
`.devcontainer/scripts/setup-gh-credential-helper.sh`

- [ ] `agentdev-runtime workspace checkout|project|catalog|config|prepare` keeps
  the clone marker, worktree validation, credential redaction, and deploy-only
  cloning.
- [ ] `agentdev-runtime project sync|hooks` and
  `agentdev-runtime git safe-directory|credential-helper` keep the managed
  `.venv` link cleanup, deploy's refusal to replace custom hooks, the skip
  variables, and the keyring-session environment read; root `AGENTS.md` and the
  microvm-sandbox skill stop naming `uv-sync.sh`.
- [ ] `agentdev-runtime project hooks`, after registering the hooks, writes one
  warning to stderr for each `language: system` hook whose `entry` executable is
  not on `PATH`, naming the hook and the executable, and keeps the exit status
  it has today; tests cover a missing and a present executable in both profiles.

### Task 12: Lifecycle commands, hooks, and the no-supervisor start

**Files:** Create: `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py`,
`py_packages/agentdev_runtime/agentdev_runtime/hooks.py`,
`py_packages/agentdev_runtime/tests/test_hooks.py`; Modify:
`docker/devcontainer/agentdev-devcontainer.Dockerfile`,
`docker/devcontainer/supervisord.conf`,
`.github/actions/run-claude-responder/action.yml`,
`scripts/tests/test_agentdev_devcontainer_lifecycle.py`,
`scripts/tests/test_agentdev_devcontainer_image.py`,
`scripts/tests/test_agentdev_devcontainer_repository.py`,
`scripts/tests/test_template_consume_migration.py`; Delete:
`.devcontainer/scripts/devcontainer-created.sh`,
`.devcontainer/scripts/devcontainer-ready.sh`,
`.devcontainer/scripts/devcontainer-attached.sh`,
`.devcontainer/scripts/run-agentdev-hooks.sh`,
`.devcontainer/scripts/postCreateCommand.sh`,
`.devcontainer/scripts/postStartCommand.sh`,
`.devcontainer/scripts/postAttachCommand.sh`

- [ ] `agentdev-runtime lifecycle created [--wait]`, `ready [--no-wait]`,
  `attached`, and `hooks <phase>` keep each phase's content and ordering, the
  hook-directory containment check, and the readiness wait. `ready --no-wait` is
  one function: start the CBM daemon, then the per-start repairs.
- [ ] The `devcontainer.metadata` label, the `created` wait program, and the
  responder action's lifecycle step name the CLI; the responder keeps its
  environment and the client-state directory creation.
- [ ] The lifecycle tests replace filename stubs with monkeypatched module
  functions, and the image, repository, and migration tests call the CLI.

### Task 13: Remove the script tree, the health report, and the acceptance wrapper

**Files:** Create: `py_packages/agentdev_runtime/agentdev_runtime/doctor.py`,
`scripts/tests/conftest.py`; Modify: `.github/workflows/ci.yml`,
`.dockerignore`, `docker/deploy/agentdev-deploy.Dockerfile`,
`docker/devcontainer/agentdev-devcontainer.Dockerfile`,
`scripts/tests/test_environment_health.py`,
`scripts/tests/test_agent_runtime_acceptance.py`; Delete:
`.devcontainer/scripts/environment-health.sh`,
`.devcontainer/scripts/ci-hooks-repro.sh`,
`.devcontainer/scripts/test-agent-runtime.sh`

- [ ] `agentdev-runtime doctor` reproduces the health report's sections, its
  PASS/FAIL/SKIP tabulation, and its exit status.
- [ ] `doctor`'s toolchain section also requires `gitleaks` and `actionlint`,
  reporting `required tool not installed` for either when it is absent.
- [ ] `ci.yml` runs the acceptance suite through `uv run pytest`; a conftest
  fixture labels and removes the containers, volumes, and networks the suite
  creates, and a session hook fails the run when every test skipped.
- [ ] The `COPY .devcontainer/scripts/` lines and the `.dockerignore` exception
  leave; `.devcontainer/scripts/` is gone from the tree, and
  `git ls-files '.devcontainer/**/*.sh'` lists only `devcontainer-init.sh`.

### Task 14: Remove Codex Cloud

**Files:** Modify: `.codex/README.md`,
`docs/knowledge/data/architecture/template-boundary.md`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`,
`docs/knowledge/data/codebase.md`,
`docs/knowledge/data/backlog/remove-agentdev-session-start-hook.md`; Delete:
`.codex/setup-codex-cloud.sh`

- [ ] The script and every reference to it are gone;
  `git grep -iE 'codex[ -]cloud'` outside `data/plans/`, `data/log.md`, the
  feature document that describes the removal, and the codebase map Task 16
  refreshes prints nothing.

### Task 15: Publisher scripts

**Files:** Create: `scripts/download-claude-responder-runs.py`,
`scripts/renovate-post-upgrade.py`,
`scripts/tests/test_download_claude_responder_runs.py`; Modify:
`.github/renovate.json`, `.github/workflows/renovate.yml`,
`scripts/analyze-claude-responder-costs.py`,
`scripts/tests/test_renovate_post_upgrade.py`,
`docs/knowledge/data/architecture/renovate-post-upgrade.md`; Delete:
`scripts/download-claude-responder-runs.sh`, `scripts/renovate-post-upgrade.sh`,
`py_packages/validate_agent_files/tests/test_download_claude_responder_runs.py`

- [ ] Both scripts are Python with the same usage and output; the responder
  download test moves out of the validator package into `scripts/tests/`; the
  Renovate `postUpgradeTasks.commands`, the `managerFilePatterns` entry, and
  `RENOVATE_ALLOWED_COMMANDS` name the `.py` file.

### Task 16: Record the decisions and refresh the references

**Files:** Create:
`docs/knowledge/data/architecture/agentdev-runtime-package.md`; Modify:
`docs/knowledge/data/architecture.md`,
`docs/knowledge/data/architecture/ci-agent-plugin-availability.md`,
`docs/knowledge/data/architecture/standalone-opencode-runtime.md`,
`docs/knowledge/data/architecture/cbm-daemon-lifecycle.md`,
`docs/knowledge/data/architecture/template-boundary.md`,
`docs/knowledge/data/architecture/module-layout.md`,
`docs/knowledge/data/architecture/uv-environment-location.md`,
`docs/knowledge/data/product.md`, `README.md`, `docker/deploy/README.md`,
`AGENTS.md`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`,
`.devcontainer/devcontainer.json`, `.devcontainer/docker-compose.yml`,
`ansible/roles/basic_prereqs/tasks/main.yml`,
`ansible/roles/dev_tools/defaults/main.yml`, `docs/knowledge/data/codebase/`

- [ ] The architecture document records the package over loose scripts, the
  `RECORD` integrity check, the firewall leaving the base image, the CBM-only
  no-supervisor start with the container-job alternatives rejected in its
  favour, and the other rejected alternatives above.
- [ ] Every document and comment that names a runtime script names the CLI
  subcommand instead; `product.md` describes the package in its stack and the
  firewall constraint by its command; root `AGENTS.md` points
  devcontainer-related code at the package.
- [ ] `/agentdev:iwe-map` refresh leaves no changed mapped source stale.

### Task 17: Verify the published image family

**Files:** None.

- [ ] **Closed by: CI on the current head.** Both architectures build the three
  images, the deploy and Dev Container acceptance jobs pass, and the canonical
  tags move.

## Spec changes

### [Firewall](../spec/firewall.md)

``` markdown
## MODIFIED Requirements

### Requirement: the firewall is inert unless explicitly enabled

`agentdev-runtime firewall apply` SHALL apply egress rules only when
`ENABLE_FIREWALL` is `true`. The runtime's bootstrap SHALL run it as root
before supervisord starts, in both profiles, so no sudoers entry is needed, and
with any other value it SHALL report that the firewall stays inert and exit 0.

#### Scenario: a container starts with no `ENABLE_FIREWALL` set

- **WHEN** the container starts
- **THEN** no egress restriction is applied.

### Requirement: enabled firewall default-DROPs IPv4 and blocks IPv6 entirely

When enabled, `agentdev-runtime firewall apply` SHALL set IPv4
`INPUT`/`FORWARD`/`OUTPUT` policies to `DROP` and block IPv6 entirely, while
preserving Docker's embedded DNS NAT rules and allowing only hosts on the
allowlist. The devcontainer profile SHALL read
`<workspace>/.devcontainer/firewall-allowlist.txt` when it exists, so
per-branch edits take effect on the next start without an image rebuild, and
`/etc/agentdev/firewall-allowlist.txt` otherwise; the deploy profile SHALL read
`FIREWALL_ALLOWLIST` or the image copy.

#### Scenario: a host not on the allowlist is requested

- **WHEN** code in the container tries to reach a non-allowlisted host
- **THEN** the connection is dropped.

#### Scenario: the checkout edits its allowlist

- **WHEN** a devcontainer restarts after `.devcontainer/firewall-allowlist.txt`
  changed in the checkout
- **THEN** the new allowlist is in force without an image rebuild.

### Requirement: the firewall self-verifies at start and fails loudly

`agentdev-runtime firewall apply` SHALL check, immediately after applying
rules, that a known-blocked host (`example.com`) fails and that
`https://api.github.com/zen` succeeds, exiting non-zero if either check goes the
wrong way, so a misconfigured firewall never silently passes as enabled while
actually open or actually blocking required traffic.

#### Scenario: the allowlist accidentally omits `api.github.com`

- **WHEN** the self-verification runs
- **THEN** the `api.github.com/zen` reachability check fails and the command
  exits non-zero, surfacing the misconfiguration at container start.

#### Scenario: the DROP policy fails to apply

- **WHEN** `example.com` is still reachable after the rules are applied
- **THEN** the verification step exits non-zero.
```

### [agentdev runtime images](../spec/agentdev-runtime-images.md)

Normative outcome: the stable lifecycle commands SHALL be
`agentdev-runtime lifecycle created`, `agentdev-runtime lifecycle ready`, and
`agentdev-runtime lifecycle attached`, published through the image's Dev
Container metadata; the bootstrap SHALL refuse to run when the installed
`agentdev_runtime` distribution differs from its recorded file hashes, which
replaces the manifest over `/opt/agentdev-runtime`; `agentdev-base` SHALL NOT
carry the package; `agentdev-runtime project hooks` SHALL warn, without failing,
about each `language: system` pre-commit hook whose executable is not on `PATH`;
and `agentdev-runtime doctor` SHALL report `gitleaks` and `actionlint` as
required tools.

### Specs that name a script

Normative outcome for each: the specification SHALL name the `agentdev-runtime`
subcommand in place of the script it names today, and every requirement and
scenario keeps its behaviour.

| Spec                                                                    | Today                                                                                                                                                                     | Subcommand                                                                                          |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| [Standalone OpenCode runtime](../spec/standalone-opencode-runtime.md)   | `runtime-health.sh status`, `runtime-supervisor.py retry`                                                                                                                 | `health status`, `supervisor retry`                                                                 |
| [CBM startup integration](../spec/cbm-startup-integration.md)           | `codebase-memory-mcp-index.sh`, `codebase-memory-mcp-install.sh`, `codebase-memory-mcp-start.sh`, `runtime-cbm.sh`, `repair-codex-cbm-hooks-block.py`                     | `cbm index`, `cbm install`, `cbm start`, `cbm run`, the `codex_hooks` module                        |
| [Claude Remote Control](../spec/claude-remote-control.md)               | `claude-remote-control-start.sh`, `-session.sh`, `-pin.sh`, `runtime-remote-control.sh`, `coder-agent-start.sh`, `preapprove-claude-workspace.sh`, `postCreateCommand.sh` | `remote-control start`, `session`, `pin`, `run`, `coder start`, `state create`, `lifecycle created` |
| [Catalog lifecycle](../spec/catalog-lifecycle.md)                       | `postCreateCommand.sh`, `postAttachCommand.sh`, `reinstall-agentdev-*.sh`, `setup-agent-state.sh`, `runtime-workspace.sh`, `codebase-memory-mcp-install.sh`               | `lifecycle created`, `lifecycle attached`, `catalog install`, `state`, `workspace`, `cbm install`   |
| [Devcontainer git credentials](../spec/devcontainer-git-credentials.md) | `coder-agent-start.sh`, `postStartCommand.sh`, `setup-gh-credential-helper.sh`                                                                                            | `coder start`, `lifecycle ready`, `git credential-helper`                                           |
| [OpenCode web](../spec/opencode-web.md)                                 | `coder-agent-start.sh`, `opencode-web-start.sh`, `opencode-web-command.sh`                                                                                                | `coder start`, `opencode coder-start`, `opencode serve`, `opencode probe`, `opencode link`          |
| [Devcontainer Docker storage](../spec/devcontainer-docker-storage.md)   | `coder-agent-start.sh`, `docker-image-prune.sh`                                                                                                                           | `coder start`, `docker prune`                                                                       |
| [Devcontainer Codex policy](../spec/devcontainer-codex-policy.md)       | `postStartCommand.sh`, `configure-codex.py`                                                                                                                               | `lifecycle ready`, `state agent-policy`                                                             |
| [Devcontainer OpenCode policy](../spec/devcontainer-opencode-policy.md) | `postStartCommand.sh`, `configure-opencode.py`                                                                                                                            | `lifecycle ready`, `state agent-policy`                                                             |
| [Coder IDE baseline](../spec/coder-ide-baseline.md)                     | `.devcontainer/scripts/coder-agent-start.sh`                                                                                                                              | `agentdev-runtime coder start`                                                                      |
| [Xpra port forwarding](../spec/xpra-port-forwarding.md)                 | `start-xpra.sh`                                                                                                                                                           | `xpra`                                                                                              |
| [Dependency updates](../spec/dependency-updates.md)                     | `scripts/renovate-post-upgrade.sh`                                                                                                                                        | `scripts/renovate-post-upgrade.py`                                                                  |

## Depends on

[Publish the reusable agentdev Dev Container
image](20261023-reusable-agentdev-devcontainer.md)

## Verification

- `uv run pytest py_packages/agentdev_runtime`
- `uv run pytest scripts/tests/test_agent_runtime_supervision.py scripts/tests/test_agent_runtime_profiles.py scripts/tests/test_agent_runtime_state.py scripts/tests/test_agent_runtime_identity.py scripts/tests/test_agent_runtime_firewall.py scripts/tests/test_agent_runtime_docker.py scripts/tests/test_agent_runtime_keyring.py scripts/tests/test_agent_runtime_cbm.py scripts/tests/test_agent_runtime_workspace.py scripts/tests/test_agent_runtime_ingress.py scripts/tests/test_runtime_remote_control.py scripts/tests/test_agentdev_devcontainer_lifecycle.py scripts/tests/test_environment_health.py scripts/tests/test_renovate_post_upgrade.py scripts/tests/test_download_claude_responder_runs.py`
- `uv run ruff check py_packages/agentdev_runtime scripts` and
  `.agents/plugins/agentdev/bin/python_lint_check.py`
- `shellcheck` on every remaining shell file;
  `git ls-files '.devcontainer/**/*.sh' 'docker/**/*.sh' '.codex/**' 'scripts/*.sh'`
  prints exactly `.devcontainer/devcontainer-init.sh`,
  `docker/ansible/setup-ansible.sh`, and `docker/desktop/entrypoint.sh`
- `uv run ansible-lint ansible` and
  `uv run ansible-playbook --syntax-check ansible/playbooks/setup-dev.yml`
- Build the three-image family locally through the repository's image-build
  action or the microVM sandbox; confirm `dpkg -l supervisor` reports nothing,
  `/opt/uv-tools/agentdev-runtime/bin/python -c 'import supervisor, tomlkit, json5, yaml'`
  succeeds, the `devcontainer.metadata` label names the CLI, and
  `agentdev-runtime doctor` passes inside a started Dev Container
- Run the direct and derived fixtures through create, stop/start, rebuild, and
  repeated attach; confirm a derived image that edits a package file fails the
  bootstrap
- Run the acceptance suite against the deploy image through the `ci.yml`
  invocation, offline for the CBM cases
- In a started Dev Container with `gitleaks` moved off `PATH`,
  `agentdev-runtime doctor` fails its toolchain section naming it, and
  `agentdev-runtime project hooks` warns about the `gitleaks` hook and exits 0
- `iwe normalize`, `iwe schema validate`, the knowledge-base tests, and an
  `/agentdev:iwe-map` refresh with no stale mapped source
- CI on the current head builds and accepts both architectures

## Out of scope

- The catalog's bundled scripts and
  `scripts/validate-super-linter-tool-versions.sh`, which sources the catalog's
  Super-Linter defaults: [Port the catalog's bundled shell scripts to
  Python](20261029-catalog-scripts-python.md).
- `.devcontainer/devcontainer-init.sh` (runs on the host under `/bin/sh -c`,
  where Python is not guaranteed), `docker/desktop/entrypoint.sh`,
  `docker/bin/gh` (a PATH shim on every `gh` call),
  `docker/ansible/setup-ansible.sh` (runs before the toolchain exists), the test
  fixtures' hook scripts, and the self-improve plugin's `si` launcher.
- Running the responder's `container:` jobs under the supervisor, decided
  against in `## Approach`; and re-pinning the toolchain-only `renovate` and
  `validate-renovate-config` jobs to `agentdev-base`, which the image-pinning
  change of [Publish the reusable agentdev Dev Container
  image](20261023-reusable-agentdev-devcontainer.md) keeps on the Dev Container
  pin.
- Publishing `agentdev_runtime` to PyPI or installing it anywhere but the two
  runtime images.
- Any other behaviour change: profile service sets, recovery budgets, catalog
  policy, the managed `.venv` link cleanup, or any spec scenario.
- The fixes for the CBM start latch and the Codex auth link, which land after
  this plan, in the package.
- Shims for the retired `/opt/agentdev-runtime/*.sh` names.

## Key references

Verified anchor points (line numbers as of 2026-10-30):

- `docker/devcontainer/agentdev-devcontainer.Dockerfile:12` — apt `supervisor`
  install
- `docker/devcontainer/agentdev-devcontainer.Dockerfile:19` —
  `COPY .devcontainer/scripts/`
- `docker/devcontainer/agentdev-devcontainer.Dockerfile:25` — sha256 runtime
  manifest
- `docker/devcontainer/agentdev-devcontainer.Dockerfile:41` —
  `devcontainer.metadata` lifecycle commands
- `docker/devcontainer/agentdev-devcontainer.Dockerfile:58` — `HEALTHCHECK`
  command
- `docker/devcontainer/agentdev-devcontainer.Dockerfile:60` — `ENTRYPOINT`
- `docker/deploy/agentdev-deploy.Dockerfile:14` — apt `supervisor` install
- `docker/deploy/agentdev-deploy.Dockerfile:22` — `COPY .devcontainer/scripts/`
- `docker/deploy/agentdev-deploy.Dockerfile:62` — `HEALTHCHECK` command
- `docker/deploy/agentdev-deploy.Dockerfile:64` — `ENTRYPOINT`
- `docker/devcontainer/supervisord.conf:25` — controller listener command
- `docker/devcontainer/supervisord.conf:38` — first service `command=`
- `docker/deploy/supervisord.conf:84` — `prepare` one-shot
- `.devcontainer/scripts/runtime-supervisor.py:79` — `SettingsParser`
- `.devcontainer/scripts/runtime-supervisor.py:306` — `DEVCONTAINER_SERVICES`
- `.devcontainer/scripts/runtime-supervisor.py:953` — bootstrap command hook
- `.devcontainer/scripts/runtime-supervisor.py:620` — `failing_dependency`, the
  client-to-dependency escalation the port keeps; `:742` — `check_once`
- `.devcontainer/scripts/runtime-supervisor.py:309` — `dockerd` is core in the
  devcontainer profile
- `.devcontainer/scripts/runtime-supervisor.py:173` — `AGENTDEV_SKIP_XPRA`
- `.github/workflows/ai-responder.yml:422` — review job `container:` block
- `.github/actions/run-claude-responder/action.yml:150` — composite
  `claude-code-action` step
- `.devcontainer/scripts/runtime-health.sh:18` — `current_state` jq parse of
  `state.json`
- `.devcontainer/scripts/runtime-bootstrap.sh:177` — `verify_runtime_root`
- `.devcontainer/scripts/runtime-bootstrap.sh:16` and
  `.devcontainer/scripts/runtime-paths.sh:6` — one variable, two defaults
- `.devcontainer/scripts/postStartCommand.sh:9` — no-supervisor branch
- `.devcontainer/scripts/configure-codex.py:1` — `uv run --script` shebang
- `.devcontainer/scripts/ci-hooks-repro.sh:20` — default image reference
- `docker/desktop/start-xpra.sh:197` — `--supervised` mode
- `ansible/roles/devcontainer_firewall/tasks/main.yml:16` — script install task
- `ansible/roles/devcontainer_firewall/tasks/main.yml:24` — sudoers task
- `ansible/roles/validate_agent_files/tasks/main.yml:61` — uv tool install to
  mirror
- `ansible/roles/validate_agent_files/defaults/main.yml:17` — `/opt/uv-tools`
- `.github/actions/run-claude-responder/action.yml:95` — lifecycle step
- `.github/workflows/ci.yml:325` — `runtime-health.sh ready` in acceptance
- `.github/workflows/ci.yml:399` — `test-agent-runtime.sh` invocation
- `.github/renovate.json:6` — `postUpgradeTasks.commands`
- `.github/workflows/renovate.yml:110` — `RENOVATE_ALLOWED_COMMANDS`
- `pyproject.toml:19` — root `supervisor` pin
- `scripts/tests/test_agentdev_devcontainer_lifecycle.py:26` — filename stubs
- `scripts/tests/test_agentdev_devcontainer_image.py:216` — patched-script
  integrity test
- `scripts/e2e/iwe-workflows/harness_codex.py:22` — Codex reinstall path
- `scripts/e2e/iwe-workflows/opencode_credential.py:24` — OpenCode start path
- `AGENTS.md:13` — `uv-sync.sh` reference
- `README.md:205` — `runtime-health.sh status` operator command
- `docker/deploy/README.md:102` — `runtime-health.sh status` operator command
- `docs/knowledge/data/product.md:112` — firewall wrapper constraint
- `docs/knowledge/data/architecture/template-boundary.md:114` — `.codex/` row
- `.codex/setup-codex-cloud.sh:4` — Codex Cloud bootstrap
- `.devcontainer/scripts/environment-health.sh:79` — required toolchain list,
  without `gitleaks` or `actionlint`
- `.devcontainer/scripts/setup-pre-commit.sh:33` — deploy hook registration;
  `:41` — devcontainer hook install, neither checking hook executables
- `.pre-commit-config.yaml:56` — `gitleaks`, a `language: system` hook; `:62` —
  `actionlint`
