---
type: plan
created: 2026-10-29
release:
- features/agentdev-runtime-cli
- bugs/workspace-image-lacks-hook-binaries
- bugs/remote-control-watcher-start-loop
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
tick](../bugs/remote-control-watcher-start-loop.md) is fixed in shell as Task
10, before the Remote Control port, so the port's baseline carries the fix.
[Bug: a CBM daemon start failure latches the standalone runtime
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

- [x] The package declares `requires-python >= 3.12`, the console script
  `agentdev-runtime`, and dependencies `supervisor` at the version the root
  project pins today, `setuptools<85`, `tomlkit`, `json5`, and `pyyaml`. The
  root project takes the package as an editable dev dependency and drops its
  direct `supervisor` and `setuptools` pins; `uv.lock` is regenerated.
  - **Evidence:** commit cfaac26; `uv lock` and `uv sync` resolve the package
    editable; `uv run pytest py_packages/agentdev_runtime` passes (26 tests).
- [x] Both runtime Dockerfiles install the package with
  `uv tool install --reinstall --python /usr/bin/python3` from the bind-mounted
  build context, with `UV_TOOL_DIR=/opt/uv-tools`,
  `UV_TOOL_BIN_DIR=/usr/local/bin`, `UV_NO_CACHE=1`,
  `UV_PYTHON_DOWNLOADS=never`, and `UV_LINK_MODE=copy`. `.dockerignore` admits
  `py_packages/agentdev_runtime`. The `COPY .devcontainer/scripts/` lines stay
  until Task 14.
  - **Evidence:** commit cfaac26; both images build locally on
    `agentdev-base:edge`, where `agentdev-runtime` resolves to `/usr/local/bin`
    and `/opt/uv-tools/agentdev-runtime/bin/python` imports `supervisor`,
    `tomlkit`, `json5`, and `yaml`.
- [x] `settings.py` parses every environment value the scripts and the
  supervisor read, with one default per variable, keyed by profile where the
  scripts disagree; the package README lists each variable, its default, and the
  profiles that read it.
  - **Evidence:** commit cfaac26;
    `py_packages/agentdev_runtime/tests/test_settings.py` checks the profile
    keying and that the README lists every declared variable, passing under
    `uv run pytest py_packages/agentdev_runtime`.

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

- [x] `runtime-supervisor.py` becomes
  `agentdev-runtime supervisor run|control|exec|retry` with its behaviour
  unchanged; the `state.json`, retry-request, and failure-record shapes live in
  `state.py` and are the only way the package reads or writes them.
  - **Evidence:** commit facf454; `test_agent_runtime_supervision.py`,
    `test_agent_runtime_profiles.py`, and `test_state.py` pass through the CLI,
    and the deploy acceptance suite passes (24, one skipped for want of a
    previous image) against `agentdev-deploy` built from that commit.
- [x] `runtime-health.sh` becomes
  `agentdev-runtime health <service>|ready|status`, reading state through
  `state.py`; user-scope probes still re-exec as the runtime user; probes call
  the service modules as they land and the remaining scripts until then.
  - **Evidence:** commit facf454; the supervision tests' `health ready` and
    `health status` cases pass, and the deploy acceptance suite and
    `test_agentdev_devcontainer_image.py` (5 passed) pass against images built
    from that commit, whose user-scope probes run as the runtime account.
- [x] `ENTRYPOINT`, `HEALTHCHECK`, the controller listener, and every `command=`
  in both supervisord configurations name the CLI, and the `exec` wrapper keeps
  its output capture and failure record. Both images stop installing the apt
  `supervisor` package, which PID 1 needs until it runs from the CLI.
  - **Evidence:** commit facf454;
    `test_shipped_config_runs_user_services_unprivileged_and_logs_to_stdout` and
    the failure-record supervision tests pass, and both images built from that
    commit boot to ready in the acceptance and image suites. The same commit
    adds `py_packages/agentdev_runtime/**` to the image path filter, points
    `ci.yml`, `devcontainer-ready.sh`, and `environment-health.sh` at the CLI,
    and renames the deleted paths in the later tasks' lifecycle, image,
    repository, migration, and acceptance tests.

### Task 3: Bootstrap and distribution integrity

**Files:** Create: `py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py`,
`py_packages/agentdev_runtime/agentdev_runtime/integrity.py`,
`py_packages/agentdev_runtime/tests/test_integrity.py`; Modify:
`scripts/tests/test_agent_runtime_identity.py`,
`scripts/tests/test_agentdev_devcontainer_image.py`,
`docker/devcontainer/agentdev-devcontainer.Dockerfile`; Delete:
`.devcontainer/scripts/runtime-bootstrap.sh`

- [x] `agentdev-runtime bootstrap` reproduces both profiles: identity validation
  and account reuse or creation, the sudoers entry through `visudo`,
  instance-storage claims that chown only an empty mount root, the shared-auth
  lock, the runtime-directory reset, and the docker group. Account and privilege
  changes stay subprocess calls to `groupadd`, `useradd`, `usermod`, `visudo`,
  and `setpriv`.
  - **Evidence:** commit c8fff30; `test_agent_runtime_identity.py` (19 passed)
    runs the bootstrap from source in containers for both profiles, and the
    deploy acceptance suite (24 passed, one skipped for want of a previous
    image) passes against `agentdev-deploy` built from that commit.
- [x] `integrity.py` verifies the installed `agentdev_runtime` distribution
  against its `RECORD` hashes and file set before the bootstrap continues, and
  refuses with the remedy `integrity.py:18` names, extending the runtime only
  through `/etc/agentdev/hooks` and documented environment. The sha256 manifest
  step leaves the Dockerfile, and the derived-image test patches a package file
  instead of a script.
  - **Evidence:** commit c8fff30; `test_integrity.py` covers patched, added, and
    removed files, a patched entry point, and a missing `RECORD`;
    `test_a_derived_image_cannot_replace_the_managed_runtime` passes in
    `test_agentdev_devcontainer_image.py` (5 passed) against
    `agentdev-devcontainer` built from that commit.

### Task 4: Firewall

**Files:** Create: `py_packages/agentdev_runtime/agentdev_runtime/firewall.py`,
`py_packages/agentdev_runtime/tests/test_firewall_allowlist.py`; Modify:
`ansible/roles/devcontainer_firewall/tasks/main.yml`,
`scripts/tests/test_agent_runtime_firewall.py`; Delete:
`ansible/roles/devcontainer_firewall/files/init-firewall.sh`,
`ansible/roles/devcontainer_firewall/files/devcontainer-firewall-sudoers`,
`.devcontainer/scripts/runtime-firewall.sh`, `.devcontainer/scripts/firewall.sh`

- [x] `agentdev-runtime firewall apply` reproduces `init-firewall.sh` and
  `runtime-firewall.sh`: the `ENABLE_FIREWALL` gate, allowlist validation,
  Docker DNS rule capture and restore, host SSH, loopback, the `allowed-domains`
  ipset from resolved A records and GitHub meta ranges collapsed with
  `ipaddress`, default DROP, established, allowlist accept, reject, the IPv6
  block, the `DOCKER-USER` chain, deploy proxy ingress, and the two
  self-verification requests. `iptables` and `ipset` run as argument lists
  through subprocess.
  - **Evidence:** commit 052196c; `test_agent_runtime_firewall.py` (14 passed)
    checks the rule sequence against a fake system and, in
    `test_proxy_ingress_egress_and_nested_docker_together`, applies the real
    rules in a privileged container on the pinned Dev Container image: egress
    blocked, GitHub and nested pulls allowed, proxy-only ingress. Deploy
    acceptance (24 passed) and the Dev Container image suite (5 passed) pass
    against images built from merge ecf005c. The network test now sets
    `AGENTDEV_RUNTIME_MODE=deploy`: against the current image pin it never
    reached proxy ingress.
- [x] The devcontainer profile reads
  `<workspace>/.devcontainer/firewall-allowlist.txt` when it exists and
  `/etc/agentdev/firewall-allowlist.txt` otherwise; deploy reads
  `FIREWALL_ALLOWLIST` or the image copy.
  - **Evidence:** commit 052196c; `test_firewall_allowlist.py` covers the
    checkout copy, the image fallback, and deploy's setting and image copy,
    passing under `uv run pytest py_packages/agentdev_runtime`.
- [x] The Ansible role keeps `iptables` and `ipset`, drops the script, the
  sudoers file, and any package only the script used once a repository grep
  confirms no other user.
  - **Evidence:** commit 052196c; the role installs only `iptables` and `ipset`.
    `dnsutils`, `iproute2`, and `aggregate` had no other user once the network
    test resolved with `getent`; `jq` and `curl` stay installed by `dev_tools`
    and `basic_prereqs`. `uv run ansible-lint ansible` and the playbook syntax
    check pass.

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

- [x] `agentdev-runtime docker run` performs the privilege, storage, private
  endpoint, and single-engine preflights and then execs `dockerd`;
  `agentdev-runtime docker prune` keeps the 72-hour filter and warning-only
  failures.
  - **Evidence:** commit cc0313b; `test_agent_runtime_docker.py` (guards, the
    exact `dockerd` argv, and a real nested engine on the pinned image) and
    `test_docker_image_prune.py` pass; deploy acceptance (24 passed) and the Dev
    Container image suite (5 passed) pass against images built from that commit.
- [x] `agentdev-runtime keyring dbus|keyring|check|wait` execs `dbus-daemon` and
  `gnome-keyring-daemon` after the bus wait, creates the login keyring once and
  never overwrites it, and `setup-keyring.sh` is deleted without a replacement.
  - **Evidence:** commit cc0313b; `test_agent_runtime_keyring.py` runs the real
    bus and keyring through the CLI (secrets served to a child, surviving
    replacement, keyring never overwritten, the bus wait); both images built
    from that commit start their supervised keyring to ready.

### Task 6: Xpra

**Files:** Create: `py_packages/agentdev_runtime/agentdev_runtime/xpra.py`;
Modify: `docker/deploy/supervisord.conf`,
`docker/devcontainer/supervisord.conf`, `docker/base/agentdev-base.Dockerfile`;
Delete: `docker/desktop/start-xpra.sh`

- [x] `agentdev-runtime xpra --supervised|--background|--stop` with `--host`,
  `--port`, and `--display` reproduces the launcher: display normalisation and
  lock clearing, orphaned X server reclaim, GPU detection and VirtualGL setup,
  the password through the environment, signal cleanup, and `exec` in supervised
  mode. The base image stops copying `/start-xpra.sh`.
  - **Evidence:** commit a595858; the supervised-Xpra cases of
    `test_agent_runtime_ingress.py` (password-gated sessions, no password on the
    command line, duplicate refusal, display reclaim after a crash) pass against
    a real Xpra through the CLI; deploy acceptance (24 passed) and the Dev
    Container image suite (5 passed) pass against images built from ba9a48d. The
    base image's own build is left to the plan's Verification.

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

- [x] `agentdev-runtime opencode serve|probe|link|coder-start` keeps the
  password requirement, the 0600 generated password file, the Coder tmux
  session, and the authenticated `/api/info` probe.
  - **Evidence:** commit ba9a48d; `test_opencode_web_start.py` (fake and real
    tmux) and the serve and probe cases of `test_agent_runtime_ingress.py` pass
    through the CLI; deploy acceptance (24 passed), whose OpenCode is supervised
    and probed by `opencode serve` and `opencode probe`, passes against
    `agentdev-deploy` built from that commit.
- [x] `agentdev-runtime coder start` runs prune, the credential helper, and the
  OpenCode start as warnings on failure, then execs the Remote Control start.
  - **Evidence:** commit ba9a48d; `test_coder_agent_start.py` (6 passed) covers
    the order, each step's failure as a warning, and the caller environment
    reaching the credential helper and the OpenCode start.

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

- [x] `agentdev-runtime cbm install|start|check|index <repo>|run|stop` keeps the
  daemon generation as PID plus `/proc` start time, the user-owned binary copy,
  the `~/.claude.json` materialise-and-restore as a context manager,
  `hooks.json` creation, the Codex hooks-block repair as a module, and the async
  index request with its acceptance check.
  - **Evidence:** commit 8e12cec; `test_agent_runtime_cbm.py` and
    `test_repair_codex_cbm_hooks_block.py` (29 passed) drive the pinned CBM
    binary through the CLI as an isolated account, including the offline
    install; `test_codebase_memory_mcp_index.py` and `test_codex_hooks.py` pass.
    `cbm install --config-only` carries the Dev Container's nonfatal wiring, and
    settings derived from the home directory follow `$HOME`, as every script
    read it. Deploy acceptance (24 passed) and the Dev Container image suite (5
    passed) pass against images built from that commit.

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

- [x] `agentdev-runtime state create|links|agent-policy|cbm` runs under one
  configuration lock, keeps deploy's fatal and the devcontainer's nonfatal CBM
  install, the user-tool registration, the auth directories, the
  `~/.claude.json` link, the Codex `auth.json` link repair, and the Claude
  pre-approval with its skip variable.
  - **Evidence:** commit 39045fa; `test_agent_runtime_state.py` (17 passed,
    including the lock taking turns across processes), `test_claude_state.py`,
    `test_codex_config.py`, `test_opencode_config.py`, and the reworked
    `test_configure_*` and `test_preapprove_claude_workspace.py` pass. Deploy
    acceptance (24 passed) and the Dev Container image suite (5 passed) pass
    against images built from 9732df9.
- [x] `agentdev-runtime catalog install <root> [--claude-scope user|local]`
  registers the Claude marketplace and plugins, the Codex marketplace with the
  already-registered short-circuit and the agents installer, and the OpenCode
  bridge entry; the complete-catalog test is one function in the package.
  - **Evidence:** commits 39045fa and 9732df9;
    `test_switching_catalogs_replaces_managed_registrations_only` and
    `test_rerunning_codex_registration_leaves_config_byte_identical` pass
    against the real Claude and Codex CLIs; deploy acceptance (24 passed,
    including the fake-`claude` Remote Control cases whose config phase
    registers the catalog) passes against `agentdev-deploy` built from 9732df9.
    `catalog complete <root>` exposes the one complete-catalog test to the shell
    lifecycle scripts until Tasks 12 and 13 replace them.

### Task 10: Remote Control watcher ends on a start that never comes up

**Files:** Modify: `.devcontainer/scripts/runtime-remote-control.sh`,
`scripts/tests/test_runtime_remote_control.py`,
`docs/knowledge/data/bugs/remote-control-watcher-start-loop.md`

- [x] When the start script returns 0 and no live `claude-remote` session
  follows, `runtime-remote-control.sh run` logs it and exits non-zero, the way a
  seen session that disappears already does, so the runtime's recovery budget
  bounds the retries; the retry that clears `checked` is gone.
  - **Evidence:** commit f8b992c; `test_runtime_remote_control.py` and
    `test_claude_remote_control_start.py` pass (38).
- [x] A test in `test_runtime_remote_control.py` runs a start that leaves no
  session and asserts the watcher exits non-zero after one start; the bug's
  `## Fix` records the fix.
  - **Evidence:** commit f8b992c;
    `test_a_start_that_never_comes_up_ends_the_watcher` asserts one start and a
    non-zero exit naming the session that did not come up; the bug's `## Fix`
    records the change.

### Task 11: Remote Control

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

- [x] `agentdev-runtime remote-control run|check|start|session [name]|pin` keeps
  the credential-signature watch, the mode and spawn validation, the
  `tmux -L claude-remote` server, the pinned-conversation resume, and the
  SessionStart hook, whose command in `--settings` becomes
  `agentdev-runtime remote-control pin`.
  - **Evidence:** commit e457d98; `test_runtime_remote_control.py`,
    `test_claude_remote_control_start.py` (fake and real tmux),
    `test_claude_remote_control_session.py`, and
    `test_claude_remote_control_pin.py` pass through the CLI. Deploy acceptance
    (24 passed, including the Remote Control login, start, and recovery cases)
    and the Dev Container image suite pass against images built from merge
    f3c202d. One image-suite run failed once, on the open CBM start latch; the
    test passed on both re-runs.

### Task 12: Workspace, project, and git helpers

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

- [x] `agentdev-runtime workspace checkout|project|catalog|config|prepare` keeps
  the clone marker, worktree validation, credential redaction, and deploy-only
  cloning.
  - **Evidence:** commit 4773feb; `test_agent_runtime_workspace.py` (25 passed,
    including the real Claude and Codex catalog registration and the offline
    hook registration) runs the command with the other modules' steps recorded.
    Deploy acceptance (24 passed), whose prepare, config, and project phases run
    it, and the Dev Container image suite (5 passed) pass against images built
    from that commit. The forced-prepare acceptance case now swaps the phase
    through `AGENTDEV_SUPERVISOR_CONFIG`, since the CLI's entry point is a
    symlink into the integrity-checked tool.
- [x] `agentdev-runtime project sync|hooks` and
  `agentdev-runtime git safe-directory|credential-helper` keep the managed
  `.venv` link cleanup, deploy's refusal to replace custom hooks, the skip
  variables, and the keyring-session environment read; root `AGENTS.md` and the
  microvm-sandbox skill stop naming `uv-sync.sh`.
  - **Evidence:** commit 4773feb; the project cases of
    `test_agent_runtime_workspace.py` and `test_setup_gh_credential_helper.py`
    pass through the CLI;
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    passes after the skill edit.
- [x] `agentdev-runtime project hooks`, after registering the hooks, writes one
  warning to stderr for each `language: system` hook whose `entry` executable is
  not on `PATH`, naming the hook and the executable, and keeps the exit status
  it has today; tests cover a missing and a present executable in both profiles.
  - **Evidence:** commit 4773feb; `test_project_hooks.py` covers a missing and a
    present executable in both profiles, a non-system hook, and deploy's
    custom-hook refusal, which exits 1 before any warning.

### Task 13: Lifecycle commands, hooks, and the no-supervisor start

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

- [x] `agentdev-runtime lifecycle created [--wait]`, `ready [--no-wait]`,
  `attached`, and `hooks <phase>` keep each phase's content and ordering, the
  hook-directory containment check, and the readiness wait. `ready --no-wait` is
  one function: start the CBM daemon, then the per-start repairs.
  - **Evidence:** commit 70828d2; `test_agentdev_devcontainer_lifecycle.py` (19
    passed) and `test_hooks.py` cover each phase's order, idempotence, the
    readiness wait and its failure, the hook order, skips, failure, and
    containment, and `ready --no-wait` starting CBM before the per-start
    repairs. The Dev Container image suite (5 passed) runs the label's commands
    against an image built from 76a1836.
- [x] The `devcontainer.metadata` label, the `created` wait program, and the
  responder action's lifecycle step name the CLI; the responder keeps its
  environment and the client-state directory creation.
  - **Evidence:** commit 70828d2;
    `test_the_responder_runs_each_phase_through_the_cli` and the profiles test
    on the `created` program pass, and the label names
    `agentdev-runtime lifecycle created|ready|attached`; the responder step
    keeps its environment and its `mkdir -p` of the client-state directories.
- [x] The lifecycle tests replace filename stubs with monkeypatched module
  functions, and the image, repository, and migration tests call the CLI.
  - **Evidence:** commit 70828d2; the lifecycle tests patch `agentdev_runtime`
    module functions in a subprocess bootstrap, and the image, repository, and
    migration tests reach the runtime only through `agentdev-runtime`.

### Task 14: Remove the script tree, the health report, and the acceptance wrapper

**Files:** Create: `py_packages/agentdev_runtime/agentdev_runtime/doctor.py`,
`scripts/tests/conftest.py`; Modify: `.github/workflows/ci.yml`,
`.dockerignore`, `docker/deploy/agentdev-deploy.Dockerfile`,
`docker/devcontainer/agentdev-devcontainer.Dockerfile`,
`scripts/tests/test_environment_health.py`,
`scripts/tests/test_agent_runtime_acceptance.py`; Delete:
`.devcontainer/scripts/environment-health.sh`,
`.devcontainer/scripts/ci-hooks-repro.sh`,
`.devcontainer/scripts/test-agent-runtime.sh`

- [x] `agentdev-runtime doctor` reproduces the health report's sections, its
  PASS/FAIL/SKIP tabulation, and its exit status.
  - **Evidence:** commit 76a1836; `test_environment_health.py` (13 passed) runs
    the CLI against stub tools for both profiles, the firewall values, missing
    tools, failures, timeouts, and the redaction.
- [x] `doctor`'s toolchain section also requires `gitleaks` and `actionlint`,
  reporting `required tool not installed` for either when it is absent.
  - **Evidence:** commit 76a1836;
    `test_a_missing_hook_binary_fails_the_toolchain` passes for each.
- [x] `ci.yml` runs the acceptance suite through `uv run pytest`; a conftest
  fixture labels and removes the containers, volumes, and networks the suite
  creates, and a session hook fails the run when every test skipped.
  - **Evidence:** commit 76a1836;
    `uv run pytest -n 4 scripts/tests/test_agent_runtime_acceptance.py` passes
    (24, one skipped) against `agentdev-deploy` built from that commit and
    leaves no labelled container behind; selecting only the skipped upgrade case
    with the image set prints `every acceptance test was skipped` and exits 1.
- [x] The `COPY .devcontainer/scripts/` lines and the `.dockerignore` exception
  leave; `.devcontainer/scripts/` is gone from the tree, and
  `git ls-files '.devcontainer/**/*.sh'` lists only `devcontainer-init.sh`.
  - **Evidence:** commit 76a1836; both images build without the copy, and
    `git ls-files ':(glob).devcontainer/**/*.sh'` lists only
    `.devcontainer/devcontainer-init.sh`. Git's default pathspec needs the
    `:(glob)` magic for `**` to match no directory.

### Task 15: Remove Codex Cloud

**Files:** Modify: `.codex/README.md`,
`docs/knowledge/data/architecture/template-boundary.md`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`,
`docs/knowledge/data/codebase.md`,
`docs/knowledge/data/backlog/remove-agentdev-session-start-hook.md`; Delete:
`.codex/setup-codex-cloud.sh`

- [x] The script and every reference to it are gone;
  `git grep -iE 'codex[ -]cloud'` outside `data/plans/`, `data/log.md`, the
  feature document that describes the removal, and the codebase map Task 16
  refreshes prints nothing.
  - **Evidence:** commit ab09896; `git grep -iE 'codex[ -]cloud'` with the four
    exclusions as pathspecs prints nothing and exits 1;
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    and `iwe schema validate` pass.

### Task 16: Publisher scripts

**Files:** Create: `scripts/download-claude-responder-runs.py`,
`scripts/renovate-post-upgrade.py`,
`scripts/tests/test_download_claude_responder_runs.py`; Modify:
`.github/renovate.json`, `.github/workflows/renovate.yml`,
`scripts/analyze-claude-responder-costs.py`,
`scripts/tests/test_renovate_post_upgrade.py`,
`docs/knowledge/data/architecture/renovate-post-upgrade.md`; Delete:
`scripts/download-claude-responder-runs.sh`, `scripts/renovate-post-upgrade.sh`,
`py_packages/validate_agent_files/tests/test_download_claude_responder_runs.py`

- [x] Both scripts are Python with the same usage and output; the responder
  download test moves out of the validator package into `scripts/tests/`; the
  Renovate `postUpgradeTasks.commands`, the `managerFilePatterns` entry, and
  `RENOVATE_ALLOWED_COMMANDS` name the `.py` file.
  - **Evidence:** commit 07bf978; `test_renovate_post_upgrade.py` (now with a
    check that the custom manager's pattern still reads the CLI pin from the
    `.py` file) and the moved
    `scripts/tests/test_download_claude_responder_runs.py` pass, and the
    renovate-config-validator hook passes on `.github/renovate.json`.

### Task 17: Record the decisions and refresh the references

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

### Task 18: Verify the published image family

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

[Claude Remote Control](../spec/claude-remote-control.md), Task 10: the
requirement "the standalone runtime starts Remote Control when a mode is set"
gains a normative outcome. A start that returns without leaving a live
`claude-remote` session SHALL count as the session exiting, so the runtime
restarts it and, once the recovery budget is exhausted, reports degraded naming
`remote-control`, or latches failed under strict startup.

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

Verified anchor points (line numbers as of 2026-10-31):

- `.devcontainer/scripts/runtime-remote-control.sh:53` — a seen session that is
  gone ends the watcher
- `.devcontainer/scripts/runtime-remote-control.sh:62` — the `checked=""` retry
  Task 10 removes
- `scripts/tests/test_runtime_remote_control.py:185` — the disappearing-session
  test the new start-loop test sits beside
- `docker/devcontainer/agentdev-devcontainer.Dockerfile:21` —
  `COPY .devcontainer/scripts/`
- `docker/devcontainer/agentdev-devcontainer.Dockerfile:39` —
  `devcontainer.metadata` lifecycle commands
- `docker/devcontainer/agentdev-devcontainer.Dockerfile:56` — `HEALTHCHECK`
  command
- `docker/devcontainer/agentdev-devcontainer.Dockerfile:58` — `ENTRYPOINT`
- `docker/deploy/agentdev-deploy.Dockerfile:24` — `COPY .devcontainer/scripts/`
- `docker/deploy/agentdev-deploy.Dockerfile:64` — `HEALTHCHECK` command
- `docker/deploy/agentdev-deploy.Dockerfile:66` — `ENTRYPOINT`
- `docker/devcontainer/supervisord.conf:25` — controller listener command
- `docker/devcontainer/supervisord.conf:38` — first service `command=`
- `docker/deploy/supervisord.conf:84` — `prepare` one-shot
- `.github/workflows/ai-responder.yml:422` — review job `container:` block
- `.github/actions/run-claude-responder/action.yml:150` — composite
  `claude-code-action` step
- `.devcontainer/scripts/postStartCommand.sh:9` — no-supervisor branch
- `.devcontainer/scripts/ci-hooks-repro.sh:20` — default image reference
- `ansible/roles/validate_agent_files/tasks/main.yml:61` — uv tool install to
  mirror
- `ansible/roles/validate_agent_files/defaults/main.yml:17` — `/opt/uv-tools`
- `.github/actions/run-claude-responder/action.yml:95` — lifecycle step
- `.github/workflows/ci.yml:325` — `agentdev-runtime health ready` in the Dev
  Container image check
- `.github/workflows/ci.yml:399` — `test-agent-runtime.sh` invocation
- `.github/renovate.json:6` — `postUpgradeTasks.commands`
- `.github/workflows/renovate.yml:110` — `RENOVATE_ALLOWED_COMMANDS`
- `scripts/tests/test_agentdev_devcontainer_lifecycle.py:25` — filename stubs
- `AGENTS.md:13` — `uv-sync.sh` reference
- `README.md:205` — `runtime-health.sh status` operator command
- `docker/deploy/README.md:102` — `runtime-health.sh status` operator command
- `docs/knowledge/data/product.md:112` — firewall wrapper constraint
- `docs/knowledge/data/architecture/template-boundary.md:114` — `.codex/` row
- `.codex/setup-codex-cloud.sh:4` — Codex Cloud bootstrap
- `.devcontainer/scripts/environment-health.sh:78` — required toolchain list,
  without `gitleaks` or `actionlint`
- `.devcontainer/scripts/setup-pre-commit.sh:33` — deploy hook registration;
  `:41` — devcontainer hook install, neither checking hook executables
- `.pre-commit-config.yaml:56` — `gitleaks`, a `language: system` hook; `:62` —
  `actionlint`
