---
type: plan
created: 2026-10-17
release:
- features/standalone-opencode-container
description: Publish agent-opencode with shared lifecycle helpers, configurable non-root identity, supervised project services, persistent state, and external-proxy Compose deployment.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-19T14:38:38Z
sources:
- resource: docker/desktop/agent-desktop.Dockerfile
- resource: .dockerignore
- resource: .devcontainer/devcontainer.json
- resource: .devcontainer/scripts/postCreateCommand.sh
- resource: .devcontainer/scripts/postStartCommand.sh
- resource: .devcontainer/scripts/setup-keyring.sh
- resource: .devcontainer/scripts/link-codex-auth.sh
- resource: .devcontainer/scripts/setup-agent-state.sh
- resource: .devcontainer/scripts/opencode-web-command.sh
- resource: .devcontainer/scripts/opencode-web-start.sh
- resource: ansible/roles/agentic_tools/defaults/main.yml
- resource: .github/workflows/ci.yml
- resource: .github/renovate.json
- resource: https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/v0.12.1/src/main.c
- resource: https://opencode.ai/v2/docs
---

# Ship a standalone OpenCode container

## Context

[Standalone OpenCode container](../features/standalone-opencode-container.md)
defines a single-project environment operated without Coder or a Dev Containers
client. The image must own startup and persistent-state reconciliation rather
than require its project to contain lifecycle scaffolding.

[OpenCode web](../spec/opencode-web.md) supplies the Coder server and
auth/session contract. [Agent auth
persistence](../architecture/agent-auth-persistence.md) separates shared
provider logins from instance state. This work extends those building blocks
with a dedicated image, not a new default for `agent-desktop`.

[Nested Docker provisioning](../architecture/nested-docker-provisioning.md)
assigns DinD to the Dev Containers feature. The standalone image needs its own
supervised daemon; the existing devcontainer remains feature-managed. [Image
pinning](../spec/image-pinning.md) applies to the new consumer examples and
publishing flow as well.

[Make OpenCode v2 the devcontainer default](20261018-opencode-v2-default.md)
replaces the image's OpenCode with v2 (`@opencode/cli` 2.0.32), and
`agent-opencode` inherits it from `agent-desktop`. That plan ships first; this
plan adapts the runtime to it. The v2 facts this plan relies on, for
`opencode serve` 2.0.32 (the `agentic_tools_opencode_version` pin):

- **Logins.** Provider logins and sessions share one SQLite database,
  `~/.local/share/opencode/opencode.db`. v2 imports an existing `auth.json` once
  and never writes it.
- **API.** The API is under `/api/`, requires the server password (basic auth,
  user `opencode`), and wraps results in `{data: ...}`: `POST /api/session`
  returns `{data: {id, ...}}`, `GET /api/session` returns `{data: [...]}`.
  `GET /api/info` returns `{version, ...}` and needs no workspace.
- **No health route.** v2 has no `/global/health`. Any path outside `/api/`,
  including `/global/health`, `/session`, and `/`, returns the web UI page with
  status 200 and no password.
- **Browser and display.** `opencode serve` opens no browser when `DISPLAY` is
  set, and a PTY child inherits `DISPLAY`.

## Approach

Derive `ghcr.io/plume-works/agent-opencode` from the same-run digest of
`agent-desktop`. Bake the canonical helpers from `.devcontainer/scripts/` into
`/opt/agentdev-runtime`; use explicit home, workspace, auth, and runtime paths
so those helpers also remain callable by the existing lifecycle hooks. Reject
copying the entire checkout into the image or invoking the root-specific hooks
unchanged. Keep `/opt/agentdev` immutable and separate from writable user state.

Use an explicitly installed foreground `supervisord` as PID 1, with a root
bootstrap for account/volume setup and root DinD, and user-owned agent services.
An event listener owns dependency transitions, bounded restart budgets,
readiness, and terminal failure. Do not rely on `startretries` alone to bound
crashes after a service reaches RUNNING. OpenCode runs foreground; retain the
existing Coder tmux launcher as an adapter over shared network/link
construction. The Coder pane is the v2 plan's: `opencode serve` without
`DISPLAY`, on `0.0.0.0` with `OPENCODE_SERVER_PASSWORD` and otherwise on
`127.0.0.1` with a generated password file. Standalone runs `opencode serve`
too, which opens no browser, and keeps DISPLAY for graphical tools spawned by
OpenCode. OpenCode readiness is an authenticated `GET /api/info` that returns a
non-empty `version`; v2 has no health route, and its public web UI page cannot
show that the API is up. Verify the web assets against the shipped version in
container acceptance.

The runtime user is `agent`, home `/home/agent`, numeric IDs from
`AGENTDEV_UID`/`AGENTDEV_GID` (both default `1000`), with passwordless sudo.
System tools live outside `/root`; user configuration is reconciled into the
runtime home after mounts. Use a per-project home volume, `/uv` volume,
workspace volume or bind, and `/var/lib/docker` volume. Share only Claude and
Codex credentials at `/var/lib/agentdev/auth`, selected through
`AGENTDEV_AGENTS_AUTH_DIR`. Require equal UID/GID within each sharing cohort;
initialize an empty shared volume under a lock, reject a populated incompatible
one, and never recursively chown the workspace, its ancestors, or another
container's credential store.

OpenCode logins are per project container. They live in v2's database in
`~/.local/share/opencode` on the instance home volume, so they survive
replacement and upgrade, and each project container logs in once. The shared
auth volume holds no OpenCode directory, and startup creates no OpenCode
credential link. Rejected:

- **Sharing OpenCode's database.** It holds the sessions as well, so sharing it
  would share sessions between project containers.
- **Sharing `auth.json`.** v2 imports it once and never writes it, so the shared
  file would carry only a stale first login.

GitHub authentication uses injected `GH_TOKEN`/`GITHUB_TOKEN`. No shared gh
configuration, interactive-login persistence facility, credential broker, or
shared keyring database is added. D-Bus and keyring remain instance-local.

Startup order is identity/mount validation, optional firewall, user
D-Bus/keyring and root DinD readiness, workspace validation/clone, auth and
client/catalog configuration, matching project setup, CBM daemon and initial
index, Xpra readiness, then OpenCode. Configure GitHub HTTPS credential handling
before a private clone. Network-facing services are reachable only through an
existing external proxy network; Compose publishes no host ports.

Implementation defaults: three recovery attempts per required service with
1/2/4-second backoff, reset only after 60 seconds continuously healthy;
60-second service-start deadlines, a configurable preparation deadline
defaulting to 1800 seconds, and a 30-second graceful-stop deadline before forced
cleanup. Tests may shorten these values. Expose configuration through documented
`AGENTDEV_*` variables, not command strings evaluated by a shell.

## Implementation Steps

### Task 1: Establish the non-root CBM lifecycle contract

**Files:** Create: `scripts/tests/test_agent_runtime_cbm.py`,
`.devcontainer/scripts/runtime-cbm.sh`

- [x] Write focused tests against the shipped CBM pin for non-root cache/home
  ownership, a mounted Git checkout, authenticated daemon status, death
  detection, restart, and graceful shutdown. Keep test repositories and caches
  below the repo-root `.tmp/`; use an isolated user/cache/endpoint so the tests
  cannot stop the developer's daemon.
  - **Evidence:** commit "feat(runtime): add the non-root CBM lifecycle
    adapter": `scripts/tests/test_agent_runtime_cbm.py` runs the v0.12.1 pin as
    UID 54321 with its own `HOME`, `CBM_CACHE_DIR`, and `CBM_RUNTIME_DIR` under
    `.tmp/`; `uv run pytest scripts/tests/test_agent_runtime_cbm.py` 8 passed
    and the developer's own daemon was still running afterwards.
- [x] Implement an adapter using the supported `daemon start/status/stop`
  interface. Track actual daemon identity and readiness, not just the
  short-lived starter process; detect generation changes and never kill a reused
  PID. Account for MCP clients auto-starting a replacement daemon. On shutdown
  close managed clients first, then stop CBM and bound any remaining process
  cleanup.
  - **Evidence:** commit "feat(runtime): add the non-root CBM lifecycle
    adapter": `.devcontainer/scripts/runtime-cbm.sh` records PID plus kernel
    start time and kills only a matching generation; check exit `5` reports a
    daemon it did not start; `run` exits nonzero on death and stops the daemon
    on SIGTERM; `stop` bounds cleanup while a client still holds the daemon.
    `shellcheck` clean. Covered by the 8-test run above.
- [x] Verify the native client-config installation under the runtime user
  preserves the image's exact CBM version/build, user-owned installation path,
  and canonical cache root without fetching an unpinned replacement. If the pin
  cannot satisfy lifecycle, installation, or ownership requirements, stop and
  revise this plan before depending on an unsupported internal daemon command,
  changing ownership of the mounted checkout, or upgrading CBM.
  - **Evidence:** commit "feat(runtime): add the non-root CBM lifecycle
    adapter": `test_install_publishes_the_exact_pinned_binary_offline` runs
    `runtime-cbm.sh install` with no network (`unshare -n`) as UID 54321; the
    installed `~/.local/bin` binary is byte-identical to the pin, user-owned,
    reports v0.12.1, is the `.claude.json` MCP command, and no default cache
    root is created.

### Task 2: Make shared auth and configuration helpers identity-aware

**Files:** Create: `.devcontainer/scripts/runtime-paths.sh`,
`.devcontainer/scripts/setup-agent-state.sh`,
`scripts/tests/test_agent_runtime_state.py`; Modify:
`.devcontainer/scripts/link-codex-auth.sh`,
`.devcontainer/scripts/link-opencode-auth.sh`,
`.devcontainer/scripts/postCreateCommand.sh`,
`.devcontainer/scripts/postStartCommand.sh`,
`.devcontainer/scripts/codebase-memory-mcp-install.sh`,
`.devcontainer/scripts/setup-gh-credential-helper.sh`

- [x] Test explicit runtime HOME/CODEX_HOME/XDG/auth roots alongside unchanged
  root devcontainer defaults, fresh/existing volumes, regular-file credential
  migration, symlink repair, and preservation of unrelated user configuration.
  - **Evidence:** commit "feat(runtime): share identity-aware agent-state
    primitives": `scripts/tests/test_agent_runtime_state.py` covers the `/root`
    defaults, fresh and populated roots, `0600` migration, destroyed/wrong-link
    repair, and untouched `config.toml`/session files; 11 passed.
- [x] Extract agent-state initialization, including `.claude.json` linking
  before CBM config installation, auth directories, Codex policy, and catalog
  registration. Let both hooks and standalone preparation call the same
  primitives; keep devcontainer scope, call order, opt-outs, and nonfatal/fatal
  behavior compatible. Standalone required operations fail explicitly.
  - **Evidence:** commit "feat(runtime): share identity-aware agent-state
    primitives": `setup-agent-state.sh create|links|codex-policy|catalog` over
    `runtime-paths.sh`; both hooks call it in their former order. Stub tests
    show `.claude.json` is linked before the CBM install, the devcontainer
    tolerates a failed CBM install while standalone stops, and only Claude gets
    the scope. The plan regression list plus the new file gave 65 passed;
    `shellcheck` clean.
- [x] Parameterize GitHub helper setup's runtime environment-file location,
  preserve an existing matching helper, and configure injected-token HTTPS
  access for clone and later Git operations without persisting tokens or
  exposing them in logs. Include private-clone ordering in the tests.
  - **Evidence:** commit "feat(runtime): share identity-aware agent-state
    primitives": `AGENTDEV_KEYRING_ENV_FILE` selects the keyring file;
    `test_injected_token_authenticates_https_before_any_checkout_exists`
    configures the helper from an empty directory, `git credential fill` returns
    the injected `GITHUB_TOKEN`, and no file or output contains it. The existing
    `test_keeps_existing_helper` still passes.

### Task 3: Share keyring setup with supervised service execution

**Files:** Create: `.devcontainer/scripts/runtime-keyring.sh`,
`scripts/tests/test_agent_runtime_keyring.py`; Modify:
`.devcontainer/scripts/setup-keyring.sh`,
`.devcontainer/scripts/setup-gh-credential-helper.sh`

- [x] Separate reusable keyring initialization/readiness/environment logic from
  lifecycle background launching. Preserve existing saved secrets and the
  existing headless keyring storage policy; never share its database between
  instances or persist session PIDs/sockets as durable state.
  - **Evidence:** commit "feat(runtime): run D-Bus and the keyring as supervised
    foreground services": `runtime-keyring.sh` holds the readiness,
    non-destructive `login.keyring` creation, and wait primitives that
    `setup-keyring.sh` now sources; the empty-password policy is unchanged.
    `test_existing_keyring_is_never_overwritten` and
    `test_no_session_state_is_persisted_in_home` pass.
- [x] Provide foreground D-Bus/keyring execution with a deterministic private
  runtime socket and explicit `XDG_RUNTIME_DIR`; make the same environment
  available to OpenCode, Xpra, CLI tools, and documented `docker exec` usage.
  Verify Secret Service access from an OpenCode-style child process, recovery
  after keyring/D-Bus replacement, and old devcontainer background behavior.
  - **Evidence:** commit "feat(runtime): run D-Bus and the keyring as supervised
    foreground services": `runtime-keyring.sh dbus|keyring` run in the
    foreground on `$XDG_RUNTIME_DIR/bus`, and `env` prints that fixed address
    for the image `ENV` and `docker exec`.
    `scripts/tests/test_agent_runtime_keyring.py` stores and reads a secret from
    a child that has only the inherited environment. It shows the keyring exits
    with its bus and the secret survives replacing both. The background
    `setup-keyring.sh` still starts and reuses a session. 7 passed, plus 6 in
    `test_setup_gh_credential_helper.py`.

### Task 4: Implement runtime identity and volume validation

**Files:** Create: `.devcontainer/scripts/runtime-bootstrap.sh`,
`scripts/tests/test_agent_runtime_identity.py`

- [x] Test default and custom numeric IDs, invalid IDs, existing account/group
  collisions, passwordless sudo, writable instance mounts, shared-auth ownership
  mismatch, and concurrent initialization of an empty auth volume.
  - **Evidence:** commit "feat(runtime): bootstrap the runtime identity and
    instance storage": `scripts/tests/test_agent_runtime_identity.py` runs the
    bootstrap in throwaway containers on named volumes. It covers 1000:1000 and
    2345:3456, five invalid IDs, the UID-collision rejection and group reuse,
    `sudo -n`, a UID-1001 auth volume rejected by UID 1000, and three concurrent
    starts with exactly one initializer. 15 passed.
- [x] Create or safely reuse the runtime account and supplementary Docker group;
  set home/runtime directories and narrowly scoped passwordless sudo. Initialize
  ownership only on managed instance storage and an empty locked credential
  volume. Reject incompatible populated state instead of recursively rewriting
  ownership. Never alter bind-checkout ownership or its ancestors.
  - **Evidence:** commit "feat(runtime): bootstrap the runtime identity and
    instance storage": `.devcontainer/scripts/runtime-bootstrap.sh` adds the
    account to `docker` and validates a per-user `sudoers.d` entry with
    `visudo`. It chowns only an empty mount root and initializes the auth volume
    under `flock` on its directory.
    `test_rejects_an_unwritable_checkout_without_changing_ownership` shows the
    bind checkout, its parent, and its file keep their owner and mode.
    `shellcheck` clean.
- [x] Keep PID/socket/runtime state ephemeral, secrets out of startup output,
  and clear errors for missing/wrong mounts, unwritable checkout, and
  incompatible UID/GID. A container restart does not rerun account migration on
  another instance's shared state.
  - **Evidence:** commit "feat(runtime): bootstrap the runtime identity and
    instance storage": every case asserts the injected password and token never
    appear in output. `test_requires_persistent_mounts` names the missing home
    volume. `test_restart_rewrites_nothing_and_resets_runtime_state` shows a
    second bootstrap reuses the account, leaves the auth and home ctime
    unchanged, and clears a stale file from `/run/user/<uid>`.

### Task 5: Prepare exactly one workspace without destructive updates

**Files:** Create: `.devcontainer/scripts/runtime-workspace.sh`,
`scripts/tests/test_agent_runtime_workspace.py`; Modify:
`.devcontainer/scripts/uv-sync.sh`, `.devcontainer/scripts/setup-pre-commit.sh`,
`.devcontainer/scripts/setup-git-safe-directory.sh`,
`.devcontainer/scripts/postAttachCommand.sh`,
`.devcontainer/scripts/reinstall-agentdev-claude.sh`,
`.devcontainer/scripts/reinstall-agentdev-codex.sh`,
`.devcontainer/scripts/reinstall-agentdev-opencode.sh`

- [x] Support `DEV_WORKSPACE_FOLDER` default `/workspaces/project`,
  `AGENTDEV_REPOSITORY_URL` for first clone, and optional
  `AGENTDEV_REPOSITORY_REF` for an initial branch/tag. A valid existing checkout
  wins without network Git operations; an empty destination without a URL or a
  nonempty invalid destination fails. Validate external Git common-directory
  access for bind-mounted worktrees and document necessary extra mounts.
  - **Evidence:** commit "feat(runtime): prepare one workspace without
    destructive updates": `runtime-workspace.sh checkout` clones `file://` at
    tag `v1` into the empty destination. It reuses a checkout whose remote was
    deleted, and rejects an empty destination without a URL and a nonempty
    non-checkout. A worktree whose main `.git` is gone fails naming the path to
    mount. `scripts/tests/test_agent_runtime_workspace.py` 20 passed.
- [x] Test dirty checkout preservation, interrupted-clone retry refusal without
  deletion, missing worktree metadata, GitHub token authentication, and clone
  errors without credentials in logs. Do not run `.venv` migration, Git reset,
  clean, fetch, pull, or branch switching against a reused workspace.
  - **Evidence:** commit "feat(runtime): prepare one workspace without
    destructive updates": tests keep the branch, HEAD, and porcelain status of a
    dirty checkout, with no `FETCH_HEAD`. A persistent clone marker refuses a
    retry over partial contents without deleting them. The gh helper runs before
    the clone, a `user:password@` URL is redacted from all output, `.venv` is
    untouched in standalone mode, and a foreign-owned checkout is trusted once.
- [x] Reuse uv synchronization only for `pyproject.toml` projects, with the
  existing all-groups/all-extras semantics and explicit `/uv` environment; run
  pre-commit setup only when its configuration exists. In strict standalone mode
  failures propagate instead of merely logging success. Respect an existing
  configured Git hook path and do not replace custom hooks silently; report
  conflicts. Test both present/absent configuration and failure paths.
  - **Evidence:** commit "feat(runtime): prepare one workspace without
    destructive updates": `runtime-workspace.sh project` gates `uv-sync.sh` and
    `setup-pre-commit.sh` on their files; parametrized tests cover absent,
    present, and failing `uv`/`pre-commit`. Standalone `setup-pre-commit.sh`
    refuses `core.hooksPath` and a non-pre-commit `pre-push` hook, leaving it
    intact. A pre-commit-generated hook is not a conflict, and the devcontainer
    path still logs a failure and exits 0.
- [x] Select a valid checkout agentdev catalog when its manifests/bridge exist,
  otherwise the image catalog. Reconcile all three clients at each container
  start, preserving unrelated config and removing stale managed registrations.
  Run configuration before CBM is started and OpenCode reads its plugins.
  Preserve default helper behavior for existing devcontainer callers.
  - **Evidence:** commit "feat(runtime): prepare one workspace without
    destructive updates": `runtime-workspace.sh catalog` picks the checkout only
    when both manifests and the bridge exist.
    `test_switching_catalogs_replaces_managed_registrations_only` runs the real
    Claude and Codex CLIs: after a checkout-to-image switch each lists only the
    image root, OpenCode keeps `other` and `theme` beside one bridge, and a user
    Codex agent survives. Ordering before CBM and OpenCode is the supervisor's
    in Task 6.

### Task 6: Supervise services and enforce readiness/recovery

**Files:** Create: `.devcontainer/scripts/runtime-supervisor.py`,
`.devcontainer/scripts/runtime-health.sh`, `docker/opencode/supervisord.conf`,
`scripts/tests/test_agent_runtime_supervision.py`

- [x] Test startup ordering, bounded deadlines, preparation failure blocking
  OpenCode, per-service recovery, dependency outages, readiness loss, and retry
  exhaustion after RUNNING as well as startup failures. Failed readiness counts
  against the same recovery budget; do not treat an endlessly hung process as
  healthy. Terminal failure must make PID 1 exit nonzero, not just stop
  children.
  - **Evidence:** commit "feat(runtime): supervise services with bounded
    recovery": `scripts/tests/test_agent_runtime_supervision.py` drives real
    supervisord 4.2.5 with the shipped config's programs swapped for scripted
    fakes. It covers the start order, preparation exit and timeout leaving
    OpenCode unstarted, a CBM crash, readiness loss, exhaustion after RUNNING
    and at startup, a hung probe, a dbus outage, and the budget reset. Every
    terminal case asserts `runtime-supervisor.py run` exits `1`. 15 passed.
- [x] Manage root DinD and user D-Bus/keyring, CBM adapter, Xpra, and OpenCode;
  use controlled foreground processes or identity-aware adapters. Pipe service
  output to stdout/stderr. Track preparation as a one-shot gate; do not rerun
  uv/catalog mutation on an ordinary individual service restart.
  - **Evidence:** commit "feat(runtime): supervise services with bounded
    recovery": `docker/opencode/supervisord.conf` runs `dockerd` as root and the
    other programs as `%(ENV_AGENTDEV_USER)s`, logging to `/dev/stdout`.
    `runtime-workspace.sh prepare` is the one-shot gate.
    `test_a_crashed_service_recovers_without_rerunning_preparation` shows one
    `prepare` and one `index` run across a recovery, and the shipped-config test
    checks each program's flags. The `dockerd` and `opencode` commands are
    written in Tasks 7 and 8.
- [x] Pause dependent readiness during recovery, refresh connection state for
  affected clients, and recover coherently after D-Bus or CBM changes without
  duplicating daemons. Publish aggregate readiness only after required probes
  pass. Handle SIGTERM with ordered shutdown: agent/client processes before CBM,
  desktop and keyring, then DinD; bound and reap entire managed process groups.
  - **Evidence:** commit "feat(runtime): supervise services with bounded
    recovery": `/run/agentdev/ready` is removed during every recovery.
    `test_dependency_outage_recovers_clients_outside_their_budget` survives a
    dbus crash that takes the keyring down even with a one-attempt budget, and a
    CBM recovery restarts OpenCode once. The SIGTERM test sees stops in the
    order `opencode, cbm, xpra, keyring, dbus, dockerd`, with exit `0`, and a
    grandchild reaped. A service ignoring SIGTERM is killed within the bound.

### Task 7: Run and persist the dedicated nested Docker engine

**Files:** Create: `.devcontainer/scripts/runtime-docker.sh`,
`scripts/tests/test_agent_runtime_docker.py`; Reuse:
`.devcontainer/scripts/docker-image-prune.sh`,
`ansible/roles/install_docker/tasks/main.yml`

- [x] Start exactly one root `dockerd` using `/etc/docker/daemon.json`, private
  Unix socket and per-instance `/var/lib/docker` storage; make it accessible to
  the runtime user without mounting the host socket or exposing a TCP listener.
  Validate privileged mode, storage backing, readiness, and replacement after a
  daemon crash. Persist all Docker data used by the shipped engine, including
  any enabled containerd image store.
  - **Evidence:** commit "feat(runtime): run a dedicated nested Docker engine":
    `.devcontainer/scripts/runtime-docker.sh` refuses missing `CAP_SYS_ADMIN`,
    overlay-backed storage, a `hosts` key, and a live second `dockerd`.
    `scripts/tests/test_agent_runtime_docker.py` runs it privileged in the
    pinned `agent-desktop` image. A UID-2000 `docker`-group user builds, no TCP
    port listens, the image survives a `SIGKILL` restart and a fresh container
    on the same volume, and the containerd store sits under
    `/var/lib/docker/containerd/daemon`. 6 passed.
- [x] Run the shared unused-image prune once the engine is ready and retain its
  nonfatal behavior and 72-hour policy; retain 10 GB BuildKit GC. Exercise
  nested `hello-world`, an actual build, engine restart, and persistent image
  reuse in the container acceptance harness. Do not also invoke a Dev Containers
  feature daemon initializer.
  - **Evidence:** commit "test(runtime): add the container acceptance harness":
    `runtime-workspace.sh prepare` runs the unchanged nonfatal
    `docker-image-prune.sh` first, after the controller has gated on `dockerd`.
    The image's `daemon.json` keeps `defaultMaxUsedSpace: 10GB`.
    `AGENTDEV_RUNTIME_TEST_IMAGE=agent-opencode:local .devcontainer/scripts/test-agent-runtime.sh`
    gave 13 passed, 1 skipped. In it, `agent` runs `hello-world`, builds an
    image, and finds that image again after a container restart and a
    replacement on the same volumes. Nothing calls a feature initializer.

### Task 8: Adapt OpenCode and Xpra for foreground proxy access

**Files:** Create: `.devcontainer/scripts/opencode-web-command.sh`,
`scripts/tests/test_agent_runtime_ingress.py`; Modify:
`.devcontainer/scripts/opencode-web-start.sh`, `docker/desktop/start-xpra.sh`,
`scripts/tests/test_opencode_web_start.py`

- [x] Extract command/link construction without changing the Coder tmux contract
  or its tests. Standalone runs OpenCode foreground in the workspace on
  `0.0.0.0:4096`, using `opencode serve` with mandatory nonempty
  `OPENCODE_SERVER_PASSWORD`. Preserve DISPLAY for agent child processes and
  test graphical tool access without opening a browser at server startup. Keep
  Coder's `opencode web` command and DISPLAY removal unchanged.
  - **Evidence:** commit "feat(runtime): serve OpenCode and Xpra for an external
    proxy": `opencode-web-command.sh` builds the link and the Coder pane, which
    `opencode-web-start.sh` now calls. The unchanged
    `test_opencode_web_start.py` and `test_coder_agent_start.py` give 22 passed.
    `scripts/tests/test_agent_runtime_ingress.py` rejects a missing or empty
    password and shows `serve --port 4096 --hostname 0.0.0.0` in the workspace
    with `DISPLAY` kept. Against a real `opencode serve`, a PTY child sees
    `DISPLAY=:100` and no browser opener runs.
- [x] Run Xpra foreground on container port 14500, with no Xpra password and
  external proxy authentication as the access boundary. Retain
  `AGENTDEV_SKIP_XPRA`; when enabled, Xpra is required for readiness and
  recovery. Add strict supervised execution without weakening existing lifecycle
  behavior.
  - **Evidence:** commit "feat(runtime): serve OpenCode and Xpra for an external
    proxy": `start-xpra.sh --supervised` fails when `xpra` is missing or a
    session is already live, and otherwise execs a foreground Xpra (default port
    14500). The `--background` and default branches are unchanged. A real Xpra
    serves its HTML5 page and accepts a `binary` WebSocket at `/` with no
    password, and a duplicate start exits `1`. Task 6's supervisor tests cover
    `AGENTDEV_SKIP_XPRA` and Xpra recovery. 8 passed.
- [x] Use authenticated OpenCode API readiness in addition to web-asset checks;
  test HTTP/WebSocket routing at the server root, password rejection, and the
  absence of host-published ports. Do not bake a Coder-specific URL, password,
  or proxy configuration into the image.
  - **Evidence:** commit "test(runtime): add the container acceptance harness":
    the `opencode` probe is `opencode-web-command.sh probe`, the authenticated
    `/global/health`. In
    `test_proxy_reaches_opencode_and_xpra_at_the_root_without_host_ports`, a
    separate proxy container forwards to the runtime. `docker port` is empty;
    health is 401 without the password and 200 with it, at the shipped version.
    The root page and its JS asset return 200, a PTY WebSocket gets 101 (401
    unauthenticated), and Xpra's page and `binary` WebSocket answer. The image
    `ENV` sets no URL, password, or proxy.

### Task 9: Preserve the opt-in firewall in standalone networking

**Files:** Create: `.devcontainer/scripts/runtime-firewall.sh`,
`scripts/tests/test_agent_runtime_firewall.py`; Reuse:
`.devcontainer/scripts/firewall.sh`,
`ansible/roles/devcontainer_firewall/files/init-firewall.sh`,
`.devcontainer/firewall-allowlist.txt`

- [x] Leave the firewall inert unless `ENABLE_FIREWALL=true`. In enabled mode,
  use an explicit allowlist or a baked default without requiring project
  scaffolding; fail on invalid configuration. Apply base rules before DinD so
  subsequent daemon network setup is not erased by a rule flush.
  - **Evidence:** commit "feat(runtime): keep the opt-in firewall in standalone
    networking": `runtime-firewall.sh` is inert for unset, `false`, and `yes`.
    It reads `FIREWALL_ALLOWLIST` or `/etc/agentdev/firewall-allowlist.txt`, and
    rejects a missing file, a non-domain entry, and missing or malformed proxy
    CIDRs before any rule. `runtime-bootstrap.sh` calls it last, before
    supervisord starts `dockerd`. `scripts/tests/test_agent_runtime_firewall.py`
    11 passed.
- [x] Allow only configured trusted proxy source CIDRs to the required web ports
  when the firewall is enabled; retain existing egress/IPv6 policy and
  self-checks. Test proxy access, forbidden egress, GitHub access, and nested
  Docker networking together. Keep the old devcontainer firewall contract
  intact.
  - **Evidence:** commit "feat(runtime): keep the opt-in firewall in standalone
    networking": the wrapper runs the unchanged `init-firewall.sh` with its
    self-checks, then accepts `AGENTDEV_TRUSTED_PROXY_CIDRS` on ports 4096 and
    14500 and applies the allowlist to forwarded traffic in `DOCKER-USER`. In a
    privileged `agent-desktop` container on a test network, the trusted IP gets
    200 on 4096 while port 5000 and an untrusted IP get nothing. Host egress to
    example.com is blocked; nested `hello-world` and GitHub work, and nested
    egress to example.com is rejected. `firewall.sh` is untouched.

### Task 10: Build the dedicated image with non-root-accessible tools

**Files:** Create: `docker/opencode/agent-opencode.Dockerfile`; Modify:
`.dockerignore`; Reuse: `docker/desktop/agent-desktop.Dockerfile`,
`ansible/roles/agentic_tools/tasks/install_catalog.yml`,
`ansible/roles/github_cli/tasks/main.yml`

- [x] Derive from an explicit supplied `agent-desktop` digest. Install
  supervisor and its required utilities explicitly. Bake helpers/config/default
  allowlist, narrowly reopening `.devcontainer/scripts` and the allowlist in
  `.dockerignore` without including `.env`, generated metadata, auth, or
  workspace contents.
  - **Evidence:** commit "feat(runtime): build the agent-opencode image":
    `docker/opencode/agent-opencode.Dockerfile` takes `FROM_IMAGE` and records
    it in `org.opencontainers.image.base.name`. It installs apt `supervisor` and
    copies `.devcontainer/scripts/`, `start-xpra.sh`, `supervisord.conf`, and
    the allowlist. `.dockerignore` reopens only `.devcontainer/scripts` and
    `.devcontainer/firewall-allowlist.txt`, with `__pycache__` still excluded.
    Built with `docker build --build-arg FROM_IMAGE=<agent-desktop pin>`;
    hadolint passes.
- [x] Audit the inherited tool inventory as the runtime user, relocating any
  root-home executables/support files to root-owned system paths and registering
  user-scoped tooling in the runtime home. Include `gh stack`, validator,
  uv/bun/node, agents, CBM, IWE, shell/lint/build tools, desktop, and Docker. Do
  not make `/root` traversable or put user-writable directories ahead of managed
  tools to hide missing installation work.
  - **Evidence:** commit "feat(runtime): build the agent-opencode image": the
    only root-home executable, the `gh-stack` extension, moves to
    `/usr/local/lib/agentdev/gh-stack`, and standalone
    `setup-agent-state.sh create` registers it in the runtime home.
    `AGENTDEV_RUNTIME_TEST_IMAGE=agent-opencode:local uv run pytest scripts/tests/test_agent_runtime_acceptance.py`
    passed: as `agent`, 17 tools resolve outside `/root` and run, as do
    `validate_agent_files` and `gh stack`. `/root` is unreadable, `sudo -n`
    works, and `~/.local/bin` is last on the image `PATH`.
- [x] Set dedicated entrypoint/CMD, user/home/path defaults, container ports,
  healthcheck, and image labels. Keep `agent-desktop` ENTRYPOINT/CMD and the
  Coder agent start compatible. Fresh user state is initialized after mounts,
  not by relying on a copied root home or first-use volume copy-up.
  - **Evidence:** commit "feat(runtime): build the agent-opencode image": the
    image sets `ENTRYPOINT runtime-supervisor.py run`, the identity and path
    `ENV`, `EXPOSE 4096 14500`, and a `HEALTHCHECK` on
    `runtime-health.sh ready`. The base account is removed and `/home/agent` is
    not created, so nothing copies up. A fresh-volume start of
    `agent-opencode:local` went `healthy` in 14 s and answered 401 without auth
    and 200 with it. `docker stop` exited `0` in 6 s, stopping `dockerd` last.
    `agent-desktop.Dockerfile` and `coder-agent-start.sh` are unchanged.

### Task 11: Supply supported Compose deployment configurations

**Files:** Create: `compose.opencode.yml`, `compose.opencode.bind.yml`,
`opencode-compose-pins.yml`, `docker/opencode/runtime.env.example`,
`scripts/tests/test_agent_runtime_compose.py`

- [x] Provide a clone-volume base and a bind-checkout override using the same
  fixed in-container workspace path. Compose creates project-scoped home, uv,
  workspace, Docker and any additional required Docker-store volumes, plus a
  named shared agent-auth volume whose name can be overridden per identity
  cohort. Verify the bind override replaces rather than duplicates the target
  workspace mount.
  - **Evidence:** commit "feat(runtime): add the standalone Compose deployment":
    `compose.opencode.yml` declares project-scoped `home`, `uv`, `docker`, and
    `workspace` volumes; Task 7 showed `/var/lib/docker` holds the whole engine.
    It also declares `agents-auth`, named
    `${AGENTDEV_AUTH_VOLUME:-agentdev-opencode-auth}`.
    `scripts/tests/test_agent_runtime_compose.py` renders it with
    `docker compose config`: `compose.opencode.bind.yml` leaves one bind mount
    at `/workspaces/project` and drops the volume. 9 passed.
- [x] Require an existing operator-named proxy network and supplied OpenCode
  password; publish no host ports, and include no MCP sidecar, Docker Desktop
  socket/secret mounts, or host Docker socket. Document privileged DinD, volume
  identity requirements, proxy routes to 4096/14500, Xpra authentication at the
  proxy, GitHub token injection, service opt-outs, and Git identity forwarding
  without empty `GIT_*` overrides.
  - **Evidence:** commit "feat(runtime): add the standalone Compose deployment":
    the network is `external` and named by the required
    `AGENTDEV_PROXY_NETWORK`, and the password is `:?`-required. Tests show
    either missing setting fails rendering without echoing the secret. The
    project has one service, no ports, no `docker.sock`, and no secrets.
    `GH_TOKEN`/`GITHUB_TOKEN`/`GIT_*` render `null` (pass-through) unless set.
    The compose comments and `docker/opencode/runtime.env.example` document each
    item, and a test checks every interpolated variable is documented.
- [x] Put the real tag-and-digest pin in root-level `opencode-compose-pins.yml`,
  outside image-build inputs, and require that override in every supported
  launch command. The final pin comes from a published image; never invent a
  digest. Validate Compose rendering for clone, bind, custom IDs, and disabled
  Xpra without printing secret values.
  - **Evidence:** commit "feat(runtime): add the standalone Compose deployment":
    the base file has no `image`, so `test_every_launch_needs_the_pin_override`
    shows a launch without `opencode-compose-pins.yml` fails. The pin file holds
    the tag only: no image is published yet, and Task 15 inserts the verified
    digest. The tests render clone, bind, custom IDs with a cohort volume, and
    disabled Xpra in a clean environment and never print the rendered config.

### Task 12: Add repeatable container acceptance tests

**Files:** Create: `.devcontainer/scripts/test-agent-runtime.sh`,
`scripts/tests/test_agent_runtime_acceptance.py`

- [x] Build a bounded acceptance harness against `AGENTDEV_RUNTIME_TEST_IMAGE`
  using isolated Compose project names, volumes, proxy fixture, temporary
  repositories and cleanup traps. Keep artifacts under repo-root `.tmp/` and do
  not spend provider/model usage for ordinary acceptance tests.
  - **Evidence:** commit "test(runtime): add the container acceptance harness":
    `.devcontainer/scripts/test-agent-runtime.sh` requires the image variable
    and runs under `timeout`. Its `EXIT` trap removes every container, volume,
    and network labelled `agentdev.test=acceptance`, and it fails a run where
    every test skipped. `scripts/tests/test_agent_runtime_acceptance.py` gives
    each container uniquely named labelled volumes and a test network. The
    `tcp_proxy.py` fixture runs in its own container, repositories live under
    `.tmp/`, and no test calls a model; without the variable the module skips.
- [x] Cover fresh bind and clone starts; non-Python and uv/pre-commit projects;
  custom IDs and sudo; real CBM query; Secret Service child access; nested
  Docker build; authenticated OpenCode API/assets; Xpra HTTP/WebSocket; and
  preparation failure keeping OpenCode unavailable.
  - **Evidence:** commit "test(runtime): add the container acceptance harness".
    The local run (13 passed) covers:
    - a bind start that skips uv and pre-commit, and a `file://` clone that
      creates `/uv/venvs/project` and a pre-commit hook;
    - `2345:3456` with `sudo -n` and owned files, and a CBM `search_graph` hit
      for `answer`;
    - a secret stored by an OpenCode PTY child and read by `docker exec`, and a
      nested build;
    - the proxy checks above;
    - an unreachable clone URL exiting `1` before `opencode` starts.
- [ ] Cover restart, replacement, an actual older/newer image upgrade with
  persistent user config, shared Claude/Codex auth files with isolated sessions
  and no shared OpenCode login state, two concurrent containers, UID mismatch
  rejection, unavailable worktree metadata, dirty-tree preservation,
  required-service crash/hang and exhausted recovery, and bounded clean stop.
  Distinguish file-persistence tests from the live provider-login check in Task
  16\.

### Task 13: Integrate native builds, manifests, pins, and CI gates

**Files:** Modify: `.github/workflows/ci.yml`,
`.github/actions/paths-filter/action.yml`, `.github/renovate.json`; Create:
`.github/workflows/opencode-runtime-checks.yml`,
`scripts/tests/test_agent_runtime_ci.py`; Reuse:
`.github/actions/docker/build-push-action/action.yml`,
`.github/actions/docker/multiarch-merge/action.yml`,
`.github/actions/docker/metadata-action/action.yml`

- [x] Build `agent-opencode` after each native desktop build using that build's
  exact digest; publish per-arch artifacts and a distinct multi-arch manifest
  using existing tag conventions. Include amd64 and arm64 acceptance jobs,
  enforce their result in the CI completion gate, and retain existing desktop
  smoke/regression jobs.
  - **Evidence:** commit "ci: build, publish, and accept agent-opencode":
    `.github/workflows/ci.yml` builds `agent-opencode` in `build-dev-image` from
    `DESKTOP_IMAGE_NAME@${{ steps.build.outputs.digest }}`, through the shared
    build-push action (per-arch digest artifacts). `merge-dev-image` merges it
    with `multiarch-merge` (shared metadata tags) and exports
    `opencode_image_pinned`. `opencode-acceptance` runs `test-agent-runtime.sh`
    on native amd64 and arm64, and `finished` needs it beside the unchanged
    jobs. `scripts/tests/test_agent_runtime_ci.py` asserts that structure;
    actionlint and zizmor pass.
- [x] Register the root Compose pin with Renovate and post-upgrade file filters.
  A pin-only update runs acceptance against the proposed digest without
  rebuilding the image or creating a self-triggering publish/pin loop. Test
  path-filter and workflow behavior for runtime source changes versus pin-only
  changes.
  - **Evidence:** commit "ci: build, publish, and accept agent-opencode":
    `.github/renovate.json` adds `opencode-compose-pins.yml` to the
    docker-compose manager and `postUpgradeTasks.fileFilters`, plus an
    `agent-opencode` group. `.github/workflows/opencode-runtime-checks.yml` runs
    on pin and compose changes with read-only permissions and no build or merge.
    It skips when other files changed, requires `@sha256:`, and runs native
    acceptance on the pinned image. `test_agent_runtime_ci.py` shows seven
    runtime sources match the image filter and the three deployment files do
    not. 14 passed.

### Task 14: Document the runtime and refresh its codebase map

**Files:** Modify: `README.md`, `docs/knowledge/data/product.md`; Create:
`docs/knowledge/data/architecture/standalone-opencode-runtime.md`; Refresh:
`docs/knowledge/data/codebase/docker.md`,
`docs/knowledge/data/codebase/api-image-runtime.md`,
`docs/knowledge/data/codebase/devcontainer/scripts.md`,
`docs/knowledge/data/codebase/flow-image-build.md`, and other stale mapped
sources

- [x] Document supported bind/clone launch commands, external proxy and password
  setup, first provider login, injected GitHub tokens, stable paths, UID
  cohorts, storage lifecycle/backup, service status/logs, upgrade and failure
  recovery. Record the supervised standalone DinD design as a new scoped
  architecture document referencing the existing feature-managed devcontainer
  decision; include rejected whole-hook reuse, shared-home/auth, and tmux
  lifetime options.
  - **Evidence:** commit "docs(runtime): document agent-opencode and refresh the
    map": `README.md` `## Standalone OpenCode runtime` covers launch, proxy and
    password, logins, tokens, identity, storage and backup, status and logs,
    upgrade, and failure recovery.
    `data/architecture/standalone-opencode-runtime.md` records the supervised
    DinD design, links nested-docker-provisioning, and gives the rejected
    hook-reuse, shared-home/auth, and tmux options.
- [x] Update product distribution/runtime context and refresh maps through
  `/agentdev:iwe-map`; record only settled interfaces, not investigation
  history. Durable specs are merged from the deltas below during Ship.
  - **Evidence:** commit "docs(runtime): document agent-opencode and refresh the
    map": `data/product.md` `## Platforms` names the standalone runtime. The
    nine stale map docs and the `data/codebase.md` hub are refreshed, and
    `stale-map-docs.py` ends `RESULT=SUCCESS`.

### Task 15: Verify published native images and usable deployment pins

**Files:** Modify: `opencode-compose-pins.yml` with the verified published
digest

- [ ] **Closed by: CI and the implementing session after publication.** On the
  final candidate, built from an `agent-desktop` that ships OpenCode v2 and
  containing Tasks 17–21, read the passing amd64/arm64 acceptance results,
  inspect the published manifest and its same-run desktop ancestry, insert its
  real digest into the deployment pin, and pass pin-only acceptance. This
  external gate is separate from writing publishing code and cannot close on a
  local build.

### Task 16: Verify actual login/session continuity behind the operator proxy

**Files:** none; operator deployment of the published candidate

- [ ] **Closed by: maintainer with the external proxy and provider login.**
  Launch the documented deployment of the Task 15 candidate, connect a provider
  in OpenCode, log in to Claude Code or Codex, and create an OpenCode session;
  replace the container and upgrade to a newer tested image with the same
  volumes; verify login, session, and user config continuity. Run a second
  same-ID project container and verify it shares the Claude/Codex login, needs
  its own OpenCode provider login, and lists none of the first container's
  sessions. Verify healthy proxy access to OpenCode/Xpra and proxy protection of
  the desktop. Keep credentials out of evidence. Do not substitute synthetic
  auth JSON for this gate.

### Task 17: Keep OpenCode logins per project container

**Files:** Delete: `.devcontainer/scripts/link-opencode-auth.sh`; Modify:
`.devcontainer/scripts/setup-agent-state.sh`,
`.devcontainer/scripts/postCreateCommand.sh`,
`scripts/tests/test_agent_runtime_state.py`,
`scripts/tests/test_agent_runtime_acceptance.py`

- [x] `setup-agent-state.sh create|links` creates only the Claude and Codex auth
  directories and links only the Codex credential, in both runtime modes. The
  state tests show no `opencode` directory under the auth root, and an existing
  `~/.local/share/opencode/auth.json` left as a regular file with its content.
  - **Evidence:** the v2 plan's `2f4a17f` removed `link-opencode-auth.sh`, and
    merge `6e2c404` made `ensure_auth_dirs` create only `claude` and `codex`.
    Commit "test(runtime): keep OpenCode logins out of the shared auth volume"
    makes the standalone `create` test assert that the auth root holds only
    those two directories. `test_links_explicit_roots_on_fresh_volumes` and
    `test_migrates_regular_credentials_and_preserves_other_config` cover the
    devcontainer side. `uv run pytest scripts/tests/test_agent_runtime_state.py`
    gives 11 passed.
- [x] The two-container acceptance test shares the Codex `auth.json` and keeps
  sessions apart through `/api/session`. It also shows the second container has
  no link into the auth volume under `~/.local/share/opencode`.
  - **Evidence:** commit "test(runtime): show OpenCode logins stay per project
    container": `test_concurrent_projects_share_codex_auth_but_not_sessions`
    reads the first container's Codex `auth.json` from the second. A session
    created through `/api/session` is listed by the first and absent from the
    second. `find ~/.local/share/opencode -type l` in the second container finds
    no target under the auth volume. It is in the 13 passed against
    `agent-opencode:local` (OpenCode 2.0.32).

### Task 18: Serve the Coder pane and the standalone server on OpenCode v2

**Files:** Modify: `.devcontainer/scripts/opencode-web-command.sh`,
`.devcontainer/scripts/opencode-web-start.sh`,
`scripts/tests/test_agent_runtime_ingress.py`; Reuse:
`scripts/tests/test_opencode_web_start.py`

- [x] `opencode-web-command.sh coder-pane` prints the v2 plan's pane command and
  creates the generated password file when no Coder password is set.
  `coder-note` names that file. `opencode-web-start.sh` builds the link, the
  pane, and the note through the helper. This replaces Task 8's constraint that
  Coder's `opencode web` command stays unchanged. The v2 plan's
  `test_opencode_web_start.py` passes unchanged, and the ingress test checks
  `opencode serve --port 4096 --hostname <host>` without `DISPLAY` for both
  password states.
  - **Evidence:** merge `6e2c404` moved the v2 pane, the generated password
    file, and the note into `opencode-web-command.sh`
    (`coder-hostname|coder-pane|coder-note`), and `opencode-web-start.sh` calls
    them. `test_opencode_web_start.py` is unchanged since the v2 plan's
    `7d55cdc`; with `opencode` 2.0.32 first on `PATH`, it and
    `test_coder_agent_start.py` pass, as does
    `test_coder_pane_serves_without_display` for `''` → `127.0.0.1` and `x` →
    `0.0.0.0`.
- [x] Against a real OpenCode 2.x `opencode serve`, started with
  `opencode-web-command.sh serve`, a PTY child sees `DISPLAY` and no browser
  opener runs. `/` and the web UI's JS asset return 200, and a PTY WebSocket
  gets 101 with the password and 401 without it.
  - **Evidence:** commit "test(runtime): serve the web UI and PTYs from OpenCode
    v2": `test_opencode_serves_its_web_ui_and_websockets_at_the_root` creates
    the PTY through `/api/pty` and connects at `/api/pty/<id>/connect`. With
    `opencode` 2.0.32 first on `PATH`,
    `uv run pytest scripts/tests/test_agent_runtime_ingress.py` gives 9 passed:
    `/` and its JS asset return 200, the WebSocket returns 101 and 401, the
    child writes `DISPLAY=:100`, and no `xdg-open` runs.

### Task 19: Probe OpenCode readiness through v2's authenticated API

**Files:** Modify: `.devcontainer/scripts/opencode-web-command.sh`,
`scripts/tests/test_agent_runtime_ingress.py`,
`scripts/tests/test_agent_runtime_acceptance.py`

- [x] `opencode-web-command.sh probe` succeeds only when an authenticated
  `GET /api/info` returns a non-empty `version`. Against a real OpenCode 2.x
  server, `/api/info` returns 401 without the password and with a wrong one,
  `probe` passes with the right password and fails with a wrong one, and no test
  reads `/global/health`.
  - **Evidence:** commit "feat(runtime): probe OpenCode readiness through
    /api/info": `probe` requires a string `version` from the authenticated
    `/api/info`. `test_opencode_rejects_api_requests_without_its_password` runs
    against `opencode serve` 2.0.32 (the pin, from `./.tmp`): 401 without and
    with a wrong password, the server's own version with the right one, and
    `probe` passes and fails to match. `shellcheck` clean. The acceptance
    module's `/global/health` reads go in this task's next box.
- [x] In container acceptance, the proxy test gets 401 from `/api/info` without
  the password and the image's OpenCode version with it, and the hung-service
  test ends with a passing `/api/info` read.
  - **Evidence:** commit "test(runtime): read OpenCode readiness from /api/info
    in container acceptance":
    `test_proxy_reaches_opencode_and_xpra_at_the_root_without_host_ports` gets
    401 through the proxy without the password and the version that
    `opencode --version` prints with it.
    `test_crashed_and_hung_services_recover` ends with
    `Runtime.api('GET', '/info')` returning that version. Both are in the 13
    passed against `agent-opencode:local` (OpenCode 2.0.32), and no test reads
    `/global/health` any more.

### Task 20: Move container acceptance to v2's session API

**Files:** Modify: `scripts/tests/test_agent_runtime_acceptance.py`

- [x] `Runtime.api` calls paths under `/api/` and returns the response's `data`.
  The restart, replacement, upgrade, and two-container tests create and list
  sessions through `/api/session`. The acceptance harness passes against a
  locally built `agent-opencode` whose `opencode --version` is the
  `agentic_tools_opencode_version` pin.
  - **Evidence:** commit "test(runtime): call OpenCode v2's /api from container
    acceptance": `Runtime.api` prefixes `/api` and unwraps `data`, so every
    session and PTY call goes through `/api/session` and `/api/pty`, and the PTY
    WebSocket is `/api/pty/<id>/connect`. `agent-desktop` built from this branch
    and `agent-opencode:local` on it both report `opencode v2.0.32`.
    `AGENTDEV_RUNTIME_TEST_IMAGE=agent-opencode:local .devcontainer/scripts/test-agent-runtime.sh`
    gave 13 passed, 1 skipped (aarch64). The skip is the upgrade test, which
    needs `AGENTDEV_RUNTIME_PREVIOUS_IMAGE` (Task 12).

### Task 21: Record per-container OpenCode logins in the runtime docs

**Files:** Modify: `README.md`,
`docs/knowledge/data/architecture/standalone-opencode-runtime.md`; Refresh:
stale `docs/knowledge/data/codebase/` docs

- [x] `README.md` `## Standalone OpenCode runtime` says Claude and Codex logins
  reach every project container in the identity cohort and each project
  container logs in to OpenCode once. Its storage table lists the auth volume as
  Claude and Codex logins. The architecture document says the same and records
  the two rejected OpenCode sharing alternatives from `## Approach`.
  - **Evidence:** commit "docs(runtime): record per-container OpenCode logins":
    `README.md` `### Proxy, password, and logins` and the storage table now put
    OpenCode logins on `home` and list the auth volume as Claude and Codex
    logins. `data/architecture/standalone-opencode-runtime.md`
    `## Identity and state` records the per-container decision and the rejected
    database and `auth.json` sharing. Prettier passes.
- [x] Refresh the map docs whose sources moved through `/agentdev:iwe-map`;
  `stale-map-docs.py` ends `RESULT=SUCCESS`.
  - **Evidence:** commit "map: refresh the runtime docs for OpenCode v2"
    refreshes the five stale docs. `devcontainer/scripts` now describes `probe`
    on `/api/info` with re-verified anchors, and `devcontainer` shares only
    Claude and Codex credentials. The digests are bumped, and
    `stale-map-docs.py` ends `RESULT=SUCCESS`.

### Task 22: Authenticate Xpra sessions with `XPRA_PASSWORD`

Supersedes Task 8's proxy-only Xpra boundary: a peer on the shared proxy network
reaches port 14500 without passing the proxy.

**Files:** Modify: `docker/desktop/start-xpra.sh`,
`.devcontainer/scripts/runtime-supervisor.py`, `compose.opencode.yml`,
`docker/opencode/runtime.env.example`, `README.md`,
`docs/knowledge/data/architecture/standalone-opencode-runtime.md`; Test:
`scripts/tests/test_agent_runtime_ingress.py`,
`scripts/tests/test_agent_runtime_supervision.py`,
`scripts/tests/test_agent_runtime_compose.py`,
`scripts/tests/test_agent_runtime_acceptance.py`

- [x] When `XPRA_PASSWORD` is set, `start-xpra.sh` passes
  `--tcp-auth=env:name=XPRA_PASSWORD`, which covers the HTML5 client's WebSocket
  sessions and keeps the secret off the command line. Unset, devcontainer and
  Coder starts are unchanged.
  - **Evidence:** commit `2fe2a47` "fix(runtime): authenticate Xpra sessions
    with XPRA_PASSWORD"; `test_agent_runtime_ingress.py` rejects a missing or
    wrong password, accepts the right one, finds no secret in the Xpra
    `cmdline`, and keeps sessions open when the variable is unset.
- [x] The standalone runtime exits 1 before the bootstrap when Xpra is enabled
  and `XPRA_PASSWORD` is empty, naming both remedies; Compose passes the
  variable and `runtime.env.example` documents it.
  - **Evidence:** commits `2fe2a47` and `5df3b26` "test(runtime): accept Xpra
    only from peers holding XPRA_PASSWORD": supervision tests 19 passed, Compose
    tests 10 passed, and local container acceptance on a built image 15 passed,
    1 skipped, including a proxy-network peer refused without the password.
- [x] `README.md` and the architecture document state the requirement.
  - **Evidence:** commit "docs(runtime): require XPRA_PASSWORD for standalone
    Xpra".

## Spec changes

Create `spec/standalone-opencode-runtime` with the following full contract.
[OpenCode web](../spec/opencode-web.md), as the [OpenCode v2
plan](20261018-opencode-v2-default.md) amends it, [Devcontainer Git
credentials](../spec/devcontainer-git-credentials.md), and [Devcontainer Docker
storage](../spec/devcontainer-docker-storage.md) keep their integration-specific
requirements; shared-helper extraction preserves them. The standalone
requirements below define strict startup and injected-token behavior without
changing Coder's tmux/failure semantics.

``` markdown
## ADDED Requirements

### Requirement: a dedicated image owns a single-project runtime

`ghcr.io/plume-works/agent-opencode` SHALL derive from the corresponding digest
of `agent-desktop`, provide linux/amd64 and linux/arm64 images, and start its
environment without Coder, a Dev Containers client, or project scaffolding.
It SHALL keep Claude Code and Codex available without autostarting them and
SHALL omit Docker MCP gateway integration.

#### Scenario: an ordinary checkout is mounted

- **WHEN** an operator starts the dedicated image with valid required configuration
- **THEN** it prepares that single project and starts OpenCode and its required services using image-owned shared helpers.

#### Scenario: the existing image is used

- **WHEN** an existing consumer starts agent-desktop or runs its devcontainer hooks
- **THEN** its command defaults, Coder integration, opt-outs, and lifecycle failure semantics remain compatible.

### Requirement: runtime identity preserves workspace and credential ownership

Agent tools SHALL run with configured numeric UID/GID, default 1000:1000, and
passwordless sudo. DinD and privileged initialization SHALL have the permissions
they require. Containers sharing an agent-auth volume SHALL use the same numeric
UID/GID. Initialization SHALL NOT recursively change workspace/ancestor or
populated shared-auth ownership and SHALL reject incompatible state explicitly.

#### Scenario: a custom identity starts

- **WHEN** writable instance volumes and shared-auth ownership match the configured IDs
- **THEN** agent tools, caches, client configuration, and sudo work as that user without access to root's private home.

#### Scenario: shared ownership is incompatible

- **WHEN** an existing auth volume belongs to another identity
- **THEN** startup fails without changing its ownership or credential content.

### Requirement: startup prepares or reuses one workspace

The runtime SHALL support a bind-mounted checkout or first clone into an empty
persistent workspace, defaulting to /workspaces/project. It SHALL preserve an
existing checkout without fetch, pull, reset, clean, branch switching, or
ownership migration. It SHALL authenticate supported GitHub HTTPS operations
with injected GH_TOKEN/GITHUB_TOKEN without storing those tokens. It SHALL run
matching uv and pre-commit preparation and complete initial CBM indexing before
OpenCode becomes available; errors and timeouts SHALL fail startup.

#### Scenario: the first clone is private

- **WHEN** an empty destination, repository URL, and valid injected token are supplied
- **THEN** startup configures noninteractive HTTPS authentication before cloning and prepares the checkout without logging the token.

#### Scenario: a dirty checkout restarts

- **WHEN** the workspace has local edits and a selected branch
- **THEN** startup preserves the branch and edits, performs only the supported project preparation, and does not automatically contact Git remotes.

#### Scenario: preparation cannot complete

- **WHEN** required worktree metadata is absent, a nonempty destination is invalid, a custom hook conflicts, setup fails, or indexing times out
- **THEN** startup reports the cause and OpenCode remains unavailable.

### Requirement: state survives replacement without cross-project session sharing

The runtime SHALL persist workspace, instance home/configuration, keyrings,
caches/environments, OpenCode provider logins and sessions, and nested Docker
storage. Only Claude and Codex provider credentials SHALL be shared across
project containers; OpenCode provider logins SHALL stay with the instance.
Startup SHALL repair the shared credential links and reconcile managed
client/catalog configuration after mounts on every container start while
preserving unrelated settings and session data. It SHALL NOT add shared
interactive GitHub-login storage.

#### Scenario: an image is upgraded with existing volumes

- **WHEN** a newer image starts against compatible persisted state
- **THEN** required managed configuration is current and provider logins, sessions, and unrelated user configuration remain usable.

#### Scenario: two project containers run

- **WHEN** same-ID containers mount the same agent-auth volume and different instance volumes
- **THEN** they see shared Claude and Codex credentials but have independent OpenCode logins, sessions, keyring databases, caches, and Docker engines.

### Requirement: required services have supervised bounded recovery

The runtime SHALL supervise OpenCode, DinD, CBM, D-Bus/keyring, and enabled Xpra
with readiness probes, bounded startup, bounded per-service retries/backoff,
and orderly termination. It SHALL detect actual daemon failure even when the
public tool daemonizes. It SHALL mark dependency outages unready, recover
affected clients coherently, and exit nonzero after recovery exhaustion.
Xpra SHALL start by default with an explicit disable option.

#### Scenario: a running service fails

- **WHEN** a required process exits or fails readiness
- **THEN** the runtime becomes unready and restarts that service within its recovery budget without duplicating daemons or rerunning project mutation unnecessarily.

#### Scenario: failures continue

- **WHEN** a service exhausts its bounded recovery budget
- **THEN** remaining managed processes stop and the container exits nonzero.

#### Scenario: the container is stopped

- **WHEN** PID 1 receives SIGTERM
- **THEN** it stops managed clients and services in dependency order, bounds shutdown, and reaps remaining processes.

### Requirement: browser access uses an external proxy

Supported Compose deployments SHALL publish no host ports and SHALL connect to
an operator-provided proxy network. OpenCode SHALL require a nonempty server
password and bind container port 4096 on a network-reachable interface. Enabled
Xpra SHALL serve port 14500 and SHALL require `XPRA_PASSWORD` for every session,
read from its environment rather than its command line; the runtime SHALL refuse
to start with Xpra enabled and no nonempty `XPRA_PASSWORD`. Devcontainer and
Coder starts SHALL NOT require it. OpenCode readiness SHALL be an
authenticated API response and SHALL NOT be inferred from a response that does
not require the password.

#### Scenario: a password is missing

- **WHEN** the standalone runtime has no nonempty OpenCode server password
- **THEN** configuration validation fails instead of exposing an unauthenticated service or a silently unreachable loopback listener.

#### Scenario: Xpra is enabled without its password

- **WHEN** the standalone runtime starts with `AGENTDEV_SKIP_XPRA` empty and no nonempty `XPRA_PASSWORD`
- **THEN** it exits nonzero before the bootstrap, naming `XPRA_PASSWORD` and `AGENTDEV_SKIP_XPRA=1`.

#### Scenario: a peer on the proxy network connects to Xpra directly

- **WHEN** another container on the proxy network opens an Xpra session on port 14500
- **THEN** the session is refused without the correct `XPRA_PASSWORD` and accepted with it.

#### Scenario: proxy requests reach the runtime

- **WHEN** an authorized user accesses the configured proxy routes
- **THEN** OpenCode API/assets and Xpra HTTP/WebSocket work, and OpenCode rejects API requests lacking its password.

### Requirement: nested Docker and opt-in firewall retain their policies

The runtime SHALL operate its own persisted DinD engine through a private Unix
socket, without a host socket mount or Docker TCP listener. It SHALL retain
10 GB BuildKit GC and startup pruning of unused images older than 72 hours,
with prune errors nonfatal. The egress firewall SHALL remain opt-in; enabled
configuration SHALL retain its allowlist/IPv6 policy and self-checks while
supporting explicitly trusted proxy ingress and nested Docker operation.

#### Scenario: the engine restarts

- **WHEN** the container or nested daemon is replaced using its persistent storage
- **THEN** its existing images remain available and builds run as the runtime user.

#### Scenario: the firewall is enabled

- **WHEN** a valid allowlist and trusted proxy sources are configured
- **THEN** required proxy access and nested builds work, forbidden egress remains blocked, and daemon network rules are not erased by startup ordering.
```

Add to [Catalog lifecycle](../spec/catalog-lifecycle.md), preserving all current
requirements and scenarios:

``` markdown
## ADDED Requirements

### Requirement: standalone startup selects and reconciles the runtime catalog

Standalone agent-opencode startup SHALL use a valid checkout-provided agentdev
catalog when present and otherwise the immutable image catalog. It SHALL
reconcile Claude, Codex, and OpenCode configuration as the runtime user after
mounts and before OpenCode starts, including generated Codex agents, without
removing unrelated user settings or agents.

#### Scenario: the project provides the catalog

- **WHEN** the checkout contains the required catalog manifests and bridge
- **THEN** all three clients use that checkout catalog for the container start.

#### Scenario: a catalog is absent or the image is upgraded

- **WHEN** a checkout has no catalog or a newer bundled catalog is selected
- **THEN** startup applies the selected bundled catalog over stale managed registrations and preserves unrelated configuration.
```

Add to [Image pinning](../spec/image-pinning.md), preserving all current
requirements and scenarios:

``` markdown
## ADDED Requirements

### Requirement: standalone runtime deployment is digest-pinned and tested

Supported agent-opencode Compose launch commands SHALL include a tag-and-digest
pin in root-level opencode-compose-pins.yml. Runtime builds SHALL use the exact
agent-desktop digest from their build run. Pin-only changes SHALL exercise the
proposed runtime image on supported architectures without rebuilding/publishing
the image they consume.

#### Scenario: runtime sources change

- **WHEN** a runtime image is built and published
- **THEN** native amd64 and arm64 builds and acceptance checks gate success and the manifest identifies the corresponding desktop ancestry.

#### Scenario: only a deployment digest changes

- **WHEN** Renovate advances opencode-compose-pins.yml
- **THEN** acceptance runs against that digest, the image-build path filter does not match, and the update does not create a publish/pin loop.
```

## Depends on

[Autostart the OpenCode web UI on
Coder](20261016-opencode-web-coder-autostart.md) and [Make OpenCode v2 the
devcontainer default](20261018-opencode-v2-default.md) must ship first.

## Verification

- Run focused pytest files from each task before its checkbox is ticked.
  Existing regression commands include
  `uv run pytest scripts/tests/test_opencode_web_start.py scripts/tests/test_coder_agent_start.py scripts/tests/test_setup_gh_credential_helper.py scripts/tests/test_configure_codex.py scripts/tests/test_repair_codex_cbm_hooks_block.py scripts/tests/test_preapprove_claude_workspace.py scripts/tests/test_docker_image_prune.py`.
- Run `uv run pytest scripts/tests/test_agent_runtime_*.py` for the runtime unit
  contracts; container acceptance is explicitly selected with
  `AGENTDEV_RUNTIME_TEST_IMAGE=<tested-tag-and-digest> uv run pytest scripts/tests/test_agent_runtime_acceptance.py`.
  Container tests without that input skip rather than accidentally using an
  unrelated local image; required CI supplies it and rejects an all-skipped run.
- Tests that start a real `opencode serve` run where `opencode --version`
  reports the `agentic_tools_opencode_version` pin; a devcontainer still on
  OpenCode v1 does not close Tasks 18 and 19. Without the rebuilt image, install
  the pin with `bun add --trust @opencode/cli@<pin>` under `./.tmp/` and put its
  `node_modules/.bin` first on `PATH`.
- Run ShellCheck on new/changed shell files, the repository Python lint check on
  new Python files, and workflow/Dockerfile/Compose lint via the existing
  pre-commit configuration. Validate actual Compose clone/bind renderings.
- Use the local build's explicit desktop digest for
  `docker build --build-arg FROM_IMAGE=<desktop-tag-and-digest> -f docker/opencode/agent-opencode.Dockerfile -t agent-opencode:local .`;
  run the acceptance harness against that image. CI repeats real acceptance on
  native amd64 and arm64; QEMU-only checks do not close native gates.
- Tasks 15 and 16 are separate external acceptance gates and must retain their
  named closer until actually observed. No provider/model usage is required for
  unit/ordinary container tests; any explicitly authorized model check uses
  `openai/gpt-6.1-sol` and `openai/gpt-6-luna`.
- Run `iwe normalize` and `iwe schema validate`; run `/agentdev:iwe-verify`
  against this plan and its full deltas before Ship merges durable specs.

## Verification results

Recorded 2026-10-18 at `afae3a2`.

- **Unit and regression suites.** The `## Verification` regression list plus
  `scripts/tests/test_agent_runtime_*.py` gave 181 passed, 14 skipped; the skips
  are the acceptance module, which needs `AGENTDEV_RUNTIME_TEST_IMAGE`.

- **Container acceptance.** `agent-opencode:local`, built from the pinned
  `agent-desktop` digest, gave 13 passed, 1 skipped under
  `.devcontainer/scripts/test-agent-runtime.sh`. The skip is the upgrade test,
  which needs `AGENTDEV_RUNTIME_PREVIOUS_IMAGE` and so a published image. Only
  amd64 ran locally; the native arm64 gate is CI's.

- **Lint.** ShellCheck on every `.devcontainer/scripts/*.sh` and
  `start-xpra.sh`, the repository Python lint, hadolint, actionlint, zizmor, and
  Prettier pass. `iwe normalize` and `iwe schema validate` exit 0, and
  `stale-map-docs.py` ends `RESULT=SUCCESS`.

- **Open gates.** Task 12's third box stays open until an older published image
  exists for the upgrade case. Task 15 needs the first CI publication and its
  real digest in `opencode-compose-pins.yml`, which is tag-only until then. Task
  16 is the maintainer's proxy and login check. `opencode-runtime-checks.yml` is
  a required check only once branch protection lists it.

- **Implementation choices within the Approach.** These shape later work:

  - PID 1 runs `supervisor.supervisord.main()` in-process, because supervisord
    itself always exits `0`.
  - The one-shot preparation gate is `runtime-workspace.sh prepare`.
  - The image bakes its own `start-xpra.sh`, because the desktop base can
    predate `--supervised`.
  - Recovery kills a crashed service's leftover process group, and supervised
    Xpra reclaims an orphaned X server.

  The settled design is in [Standalone OpenCode
  runtime](../architecture/standalone-opencode-runtime.md) and [CBM daemon
  lifecycle](../architecture/cbm-daemon-lifecycle.md).

- **Defect found, not absorbed.** With the firewall enabled, Docker Hub pulls
  fail on the CloudFront CDN host; filed as [Bug: firewalled Docker Hub pulls
  fail at the CloudFront CDN](../bugs/firewall-docker-hub-cloudfront.md).

- **The results above predate OpenCode v2.** They were taken on OpenCode 1.19.3.
  Against `opencode serve` 2.0.32, `/global/health` returns the web UI page with
  status 200 without a password, so the shipped `probe` would never pass and the
  container would never become ready. Tasks 17–21 adapt the runtime, and the
  acceptance results are retaken on a v2 image.

- **On OpenCode v2, recorded 2026-10-19 at `f340d45`.**

  - Container acceptance against `agent-opencode:local` gave 13 passed, 1
    skipped (the upgrade test) on aarch64. That image is built on an
    `agent-desktop` built from this branch, and both report OpenCode 2.0.32.
  - The regression list plus `test_agent_runtime_*.py` gave 172 passed, 16
    skipped, 8 failed, with 2.0.32 first on `PATH`. The failures are in
    `test_agent_runtime_cbm.py` and one `test_agent_runtime_identity.py` case.
    Their code and tests are unchanged since `48bd5e5`. The checkout ran on a
    `fuse.grpcfuse` mount, which ignores ownership and mode and cannot host the
    daemon socket for another UID. They need a rerun on a native filesystem,
    such as CI.
  - ShellCheck, `iwe schema validate`, and `stale-map-docs.py` pass.

## Out of scope

- Multiple projects per running container, automatic repository updates,
  destructive checkout repair, and ownership migration of existing user state.
- Shared credentials across different numeric identity cohorts; shared session,
  home, keyring, or Docker databases between project containers.
- Sharing OpenCode provider logins between project containers.
- Interactive GitHub-login persistence/sharing, SSH-agent/key provisioning,
  bundled reverse proxy/TLS, Docker MCP gateway/Desktop secrets integration,
  host Docker sockets, and remote Docker engines.
- Claude Remote Control autostart, changing existing Coder/Dev Containers
  defaults, catalog hot reload without restart, and a new bare-metal installer.
- Upgrading CBM to bypass a failed feasibility gate, promising concurrent
  upstream credential-write safety, or redesigning the existing firewall policy.

## Key references

Verified anchor points (line numbers as of 2026-10-17):

- `docker/desktop/agent-desktop.Dockerfile:41-68` — build-time Ansible and
  immutable catalog; `:73-86` — WORKDIR, copied launchers, entrypoint/CMD.
- `.dockerignore:6-11` — ignored Git, user state, devcontainer, and scratch
  sources.
- `.devcontainer/devcontainer.json:12-18` — feature-managed DinD/SSH; `:20-50` —
  runtime environment; `:60-108` — per-instance mounts including OpenCode.
- `.devcontainer/scripts/postAttachCommand.sh:8-16` — indexing, uv sync,
  checkout catalog registration.
- `.devcontainer/scripts/link-codex-auth.sh:19-31` — hardcoded root credential
  paths and link repair.
- `.devcontainer/scripts/codebase-memory-mcp-install.sh:22-28` — cache and
  install paths; `:54-82` — symlink restoration and native installation.
- `.devcontainer/scripts/codebase-memory-mcp-start.sh:9-19` — required
  environment, detached daemon, initial index.
- `.devcontainer/scripts/setup-keyring.sh:31-35` — checkout-relative environment
  file and user keyring; `:66-82` — non-destructive initialization; `:111-135` —
  background services/readiness.
- `.devcontainer/scripts/setup-gh-credential-helper.sh:7-30` — keyring
  environment and existing-helper-preserving GitHub setup.
- `.devcontainer/scripts/uv-sync.sh:16-32` — managed `.venv` migration and
  unconditional sync.
- `.devcontainer/scripts/setup-pre-commit.sh:8-20` — skip and hook setup/error
  behavior.
- `.devcontainer/scripts/coder-agent-start.sh:9-21` —
  prune/helper/OpenCode/Remote Control ordering.
- `.devcontainer/scripts/docker-image-prune.sh:12-20` — nonfatal 72-hour image
  prune.
- `.devcontainer/scripts/configure-codex.py:18-26` — policy and HOME/CODEX_HOME
  resolution.
- `docker/desktop/start-xpra.sh:188-244` — foreground/background mode, lifecycle
  checks, bind and D-Bus options; `:251-278` — launch paths.
- `ansible/roles/install_docker/tasks/main.yml:34-63` — Docker packages and 10
  GB BuildKit policy.
- `ansible/roles/devcontainer_firewall/files/init-firewall.sh:14-33` — allowlist
  and rule flush; `:123-163` — DROP/IPv6/self-check policy.
- `ansible/roles/agentic_tools/defaults/main.yml:75-86` — catalog location and
  staged trees.
- `ansible/roles/agentic_tools/tasks/main.yml:23-37` — global CLIs in
  /usr/local.
- `ansible/roles/agentic_tools/tasks/install_catalog.yml:85-145` — Codex agents
  and root OpenCode bridge config.
- `ansible/roles/github_cli/tasks/main.yml:43-49` — baked gh wrapper; `:94-123`
  — user-home gh-stack registration.
- `ansible/roles/dev_tools/defaults/main.yml:58-69` — shipped CBM
  version/checksums.
- `.github/workflows/ci.yml:146-158` — desktop build with same-run base digest;
  `:166-197` — manifest merge; `:246-302` — current acceptance/completion gate.
- `.github/actions/paths-filter/action.yml:35-48` — image-build input filter.
- `.github/actions/docker/build-push-action/action.yml:57-95` — per-arch digest
  publishing/artifacts.
- `.github/actions/docker/multiarch-merge/action.yml:67-120` — manifest and
  pinned output.
- `.github/actions/docker/metadata-action/action.yml:50-59` — existing
  publication tag conventions.
- `.github/renovate.json:5-32` — post-upgrade filters and Compose pin discovery;
  `:42-49` — current image grouping.
- `docs/knowledge/data/spec/catalog-lifecycle.md:20-134` — current catalog
  installation and shared-agent-auth scope.
- `docs/knowledge/data/spec/image-pinning.md:16-65` — digest policy and pin-loop
  avoidance.
- `docs/knowledge/data/architecture/nested-docker-provisioning.md:21-39` —
  feature-owned DinD decision.
- `README.md:25-69` — current images, adoption, and digest policy.

Verified anchor points (line numbers as of 2026-10-19):

- `.devcontainer/scripts/postCreateCommand.sh:56` —
  `setup-agent-state.sh create`; `:70` — staged-catalog install.
- `.devcontainer/scripts/postStartCommand.sh:27` — `setup-agent-state.sh links`;
  `:30` — `agent-policy`.
- `.devcontainer/scripts/setup-agent-state.sh:41` — `ensure_auth_dirs`; `:65` —
  `link_auth`; `:69` — `cmd_create`.
- `.devcontainer/scripts/opencode-web-command.sh:10` — generated password file;
  `:19` — `link`; `:29` — `coder_hostname`; `:39` — `coder_pane`; `:52` —
  `coder_note`; `:62` — `probe`, reading `/global/health`; `:76` — `serve`.
- `.devcontainer/scripts/opencode-web-start.sh:14-37` — helper calls, session
  reuse, and the tmux launch.
- `.devcontainer/scripts/runtime-health.sh:33` — the `opencode` probe.
- `ansible/roles/agentic_tools/defaults/main.yml:10` —
  `agentic_tools_opencode_version`.
- `scripts/tests/test_agent_runtime_state.py:111` —
  `test_links_explicit_roots_on_fresh_volumes`; `:122` —
  `test_migrates_regular_credentials_and_preserves_other_config`; `:143` —
  `test_repairs_destroyed_and_wrong_links`.
- `scripts/tests/test_agent_runtime_ingress.py:89` —
  `test_coder_pane_serves_without_display`; `:151` — `opencode_server`; `:175` —
  `test_opencode_rejects_requests_without_its_password`; `:187` —
  `test_opencode_serves_its_web_ui_and_websockets_at_the_root`.
- `scripts/tests/test_agent_runtime_acceptance.py:166` — `Runtime.api`; `:380` —
  `test_proxy_reaches_opencode_and_xpra_at_the_root_without_host_ports`; `:489`
  —
  `test_restart_and_replacement_keep_the_dirty_tree_config_sessions_and_images`;
  `:523` — `test_upgrade_from_the_previous_image_keeps_user_state`; `:540` —
  `test_concurrent_projects_share_codex_auth_but_not_sessions`; `:578` —
  `test_crashed_and_hung_services_recover`.
- `README.md:111-114` — login sharing; `:133` — the auth volume's storage row.
- `docs/knowledge/data/architecture/standalone-opencode-runtime.md:53-58` — the
  shared-credential decision.
