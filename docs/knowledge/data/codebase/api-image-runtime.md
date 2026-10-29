---
type: codebase
description: 'What a consumer of the ghcr.io/plume-works agentdev-base, agentdev-devcontainer and agentdev-deploy images can rely on: environment variables each image reads, files and tools it provides, labels, ports, and, for the runtime images, entrypoint, health, and volumes.'
source:
- docker
- ansible/roles/agentic_tools
- ansible/roles/devcontainer_firewall
- compose.opencode.yml
source_digest: sha256:ac42a6ace816082c13c096c6e81425795386b32189b0d40d4f3cc84835c2522a
verified:
  by: claude-code/opus-5.5
  at: 2026-10-29T21:16:01Z
stale_after: 2027-01-27
generated:
  by: claude-code/opus-5.5
  at: 2026-10-29T21:16:01Z
sources:
- id: code
  resource: docker
---

# Interface: image runtime contract

The published images are consumed by this repository's Dev Container, by
Codespaces, by any project pointing its own `devcontainer.json` at
`agentdev-devcontainer` or deriving an image from it, and by `agentdev-deploy`
operators. This is the surface those consumers touch; the build that produces it
is [docker/](docker.md) plus [ansible/](ansible.md).

## Images

All four are multi-arch `linux/amd64` + `linux/arm64`, published under an
immutable `sha-<commit>` tag and promoted to `edge` or `pr-<N>` after
acceptance.

- `ghcr.io/plume-works/ubuntu-ansible` — the Ansible base
- `ghcr.io/plume-works/agentdev-base` — the lifecycle-neutral tools, staged
  catalog, and default policy, built on `ubuntu-ansible`
- `ghcr.io/plume-works/agentdev-devcontainer` — the Dev Container runtime, built
  on the same run's `agentdev-base` digest; pinned by tag and digest in
  `devcontainer-compose-pins.yml` and every workflow `container.image`
- `ghcr.io/plume-works/agentdev-deploy` — the standalone runtime, built on the
  same run's `agentdev-base` digest; pinned in `opencode-compose-pins.yml`
- Both runtime images carry `org.opencontainers.image.base.name` with that
  digest — `docker/deploy/agentdev-deploy.Dockerfile:53`,
  `docker/devcontainer/agentdev-devcontainer.Dockerfile:53`
- Labels `org.opencontainers.image.version.agentdev`,
  `org.opencontainers.image.version.playwright`, and
  `org.opencontainers.image.version.validate-agent-files`, inherited from
  `docker/base/agentdev-base.Dockerfile:80-82`

## Environment the image reads

| Variable                                            | Read by                                                                    | Meaning                                                                  |
| --------------------------------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `DEV_WORKSPACE_FOLDER`                              | firewall allowlist lookup, lifecycle scripts                               | the mounted workspace; falls back to the baked `WORKSPACE_FOLDER`        |
| `ENABLE_FIREWALL`                                   | `.devcontainer/scripts/firewall.sh`                                        | `true` applies `init-firewall.sh`; anything else leaves it inert         |
| `FIREWALL_ALLOWLIST`                                | `init-firewall.sh:14`                                                      | overrides the allowlist path                                             |
| `XPRA_HOST`, `XPRA_VIDEO_ENCODERS`, `XPRA_LOG_FILE` | `/start-xpra.sh:6-14`                                                      | bind host, encoders, log path                                            |
| `XPRA_PASSWORD`                                     | `/start-xpra.sh:285-287`                                                   | nonempty: every TCP/WebSocket session must authenticate with it          |
| `AGENTDEV_CATALOG_DIR`                              | set by `agentdev-base.Dockerfile:75`, read by `devcontainer-created.sh:51` | where the catalog is staged (`/opt/agentdev`)                            |
| `PLAYWRIGHT_BROWSERS_PATH`                          | set by the image                                                           | shared, runtime-writable browser binaries at `/opt/playwright`           |
| `CBM_CACHE_DIR`                                     | the `codebase-memory-mcp-*.sh` scripts                                     | required; cache and logs location                                        |
| `AGENTDEV_SKIP_PRE_COMMIT`, `AGENTDEV_SKIP_XPRA`    | `setup-pre-commit.sh` and the runtime profiles                             | opt out of hook install and desktop start                                |
| `GH_TOKEN` / `GITHUB_TOKEN`, `VERBOSE_GH`           | the `gh` wrapper                                                           | an explicit token wins; otherwise derived from the git credential helper |

## Files and tools

- `/entrypoint.sh` (`exec "$@"`), `/start-xpra.sh`,
  `/usr/local/bin/init-firewall.sh` with a NOPASSWD sudoers entry, the `gh`
  wrapper ahead of the real `gh`
- `/opt/agentdev` — the staged catalog, root-owned and read-only, with the
  plugin already installed for Claude Code and Codex at build time, its agents
  in `~/.codex/agents/agentdev-<stem>.toml`, and its OpenCode bridge listed in
  `~/.config/opencode/opencode.json`
- On `PATH`: `uv`, `bun`, `node`, `claude`, `codex`, `opencode`, `gh`, `cmake`,
  `ninja`, `shellcheck`, `zizmor`, `gitleaks`, `actionlint`, `jq`, `iwe`/`iwes`,
  `codebase-memory-mcp`, `validate_agent_files`, `playwright` with matching
  Chromium, `pre-commit`, `xpra`, `gnome-keyring-daemon`, Docker CE with buildx
  and compose
- `EXPOSE 14500` — the Xpra HTML5 container port, fixed by default and
  overridable with `/start-xpra.sh --port`; the devcontainer forwards `14500`

## agentdev-devcontainer

The image runs itself: `runtime-supervisor.py run` is PID 1 in the
`devcontainer` profile and supervises D-Bus, keyring, Docker, CBM, and Xpra as
core services, with a `runtime-health.sh ready` healthcheck and a 5-minute start
period — `docker/devcontainer/agentdev-devcontainer.Dockerfile:57-61`. Its
`devcontainer.metadata` label supplies, to every descriptor that selects it,
`privileged`, `overrideCommand: false`, a per-container volume at
`/var/lib/docker`, `DEV_WORKSPACE_FOLDER`, and the lifecycle commands —
`/opt/agentdev-runtime/devcontainer-created.sh` (`postCreateCommand`),
`devcontainer-ready.sh` (`postStartCommand`, and `waitFor`), and
`devcontainer-attached.sh` (`postAttachCommand`) — `:41-50`. A descriptor's own
lifecycle commands run in addition to those.

- A derived image extends each phase with executable files in
  `/etc/agentdev/hooks/{created,started,attached}.d/`, run in name order after
  the managed phase; a failing hook names itself and its phase —
  `.devcontainer/scripts/run-agentdev-hooks.sh:9`.
- Changing, adding, or removing a file below `/opt/agentdev-runtime` fails
  startup — `.devcontainer/scripts/runtime-bootstrap.sh:176`.
- `AGENTDEV_USER`, `AGENTDEV_HOME`, `CBM_CACHE_DIR`, and the bus and display
  defaults are overridable `ENV` — `:29-37`. OpenCode Web and Claude Remote
  Control are opt-in clients, never readiness gates.
- A mounted checkout that carries the complete agentdev catalog is registered
  over the staged one on every attach; any other workspace keeps the staged
  catalog.

## agentdev-deploy

The image runs itself:
`ENTRYPOINT ["/opt/agentdev-runtime/runtime-supervisor.py", "run"]`,
`EXPOSE 4096 14500`, and a `HEALTHCHECK` of `runtime-health.sh ready` with a
10-minute start period — `docker/deploy/agentdev-deploy.Dockerfile:57-65`. It
must run privileged, with volumes at `/home/agent`, `/uv`, `/var/lib/docker`,
`/workspaces/project` (or a bind checkout), and `/var/lib/agentdev/auth`; the
supported deployment is the root `compose.opencode.yml`.

| Variable                                                                                | Meaning                                                                                                                                                                           |
| --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `OPENCODE_SERVER_PASSWORD`                                                              | required, nonempty; OpenCode listens on `0.0.0.0:4096` behind it                                                                                                                  |
| `AGENTDEV_UID`, `AGENTDEV_GID`                                                          | numeric runtime identity, default `1000`; must match within one auth-volume cohort                                                                                                |
| `AGENTDEV_REPOSITORY_URL`, `AGENTDEV_REPOSITORY_REF`                                    | clone an empty workspace once, optionally at a branch or tag                                                                                                                      |
| `GH_TOKEN`, `GITHUB_TOKEN`                                                              | HTTPS Git through `gh`, configured before a clone; never written to disk                                                                                                          |
| `XPRA_PASSWORD`                                                                         | required, nonempty, unless `AGENTDEV_SKIP_XPRA` is true; Xpra's session password, separate from OpenCode's                                                                        |
| `AGENTDEV_SKIP_XPRA`, `AGENTDEV_STRICT_STARTUP`, `ENABLE_FIREWALL`                      | booleans: `1`/`true`/`yes`/`on` or `0`/`false`/`no`/`off`/empty, any case; strict makes every optional failure latch; the bootstrap sees the firewall switch as `true` or `false` |
| `AGENTDEV_TRUSTED_PROXY_CIDRS`, `FIREWALL_ALLOWLIST`                                    | opt-in egress firewall; proxy sources allowed to 4096/14500; allowlist override of `/etc/agentdev/firewall-allowlist.txt`                                                         |
| `AGENTDEV_RECOVERY_ATTEMPTS`, `AGENTDEV_PROBE_FAILURES`, `AGENTDEV_STOP_TIMEOUT`        | positive integers: 3 attempts, 2 failed probes, 30 s stop                                                                                                                         |
| `AGENTDEV_RECOVERY_BACKOFF`, `AGENTDEV_HEALTHY_RESET`, `AGENTDEV_SERVICE_START_TIMEOUT` | positive seconds: backoff doubling from 1, reset after 60 healthy, 60 to first readiness                                                                                          |
| `AGENTDEV_BOOTSTRAP_TIMEOUT`, `AGENTDEV_PREPARE_TIMEOUT`, `AGENTDEV_HEALTH_INTERVAL`    | positive seconds: 1800 for the bootstrap, 1800 per preparation step, 2 between controller checks                                                                                  |
| `AGENTDEV_CLAUDE_RC_MODE`, `AGENTDEV_CLAUDE_RC_SPAWN`                                   | `session` or `server` adds the `remote-control` component, empty leaves it out; in server mode the spawn mode is `worktree` (or empty) or `same-dir`                              |

Any other spelling or a non-positive value latches a configuration failure
naming the variable — `.devcontainer/scripts/runtime-supervisor.py:79`, `:159`.
`docker exec` sessions see the same `DISPLAY`, `DOCKER_HOST`, `XDG_RUNTIME_DIR`,
and `DBUS_SESSION_BUS_ADDRESS` as OpenCode's tools.

Operator surface, all through `docker exec`:

- `/run/agentdev/state.json` — `state` (`pending`, `ready`, `degraded`,
  `failed`), `latched`, each component's `status` and `reason`, and a
  `heartbeat` refreshed every interval, plus the `profile` and the core `probes`
  readiness repeats — `.devcontainer/scripts/runtime-supervisor.py:441`.
- `runtime-health.sh ready` passes only with a heartbeat under three intervals
  old, state `ready`, and every probe the state lists passing — `dbus`,
  `keyring`, and `opencode` for deploy; `runtime-health.sh status` prints the
  state, each failed or blocked component with its retry command, what
  `remote-control` is doing when it runs, and the last failure —
  `.devcontainer/scripts/runtime-health.sh:49`, `:62`.
- `~/.local/state/agentdev/last-failure.json` on the home volume — startup ID,
  component, reason, command, exit status, at most 200 output lines from the
  attempt that failed, UTC time; only a later failure replaces it —
  `.devcontainer/scripts/runtime-supervisor.py:480`.
- `runtime-supervisor.py retry [component]` — resumes a latched runtime, or
  reruns one failed component, restarts the serving clients that read it, and
  exits `0` when it succeeded —
  `.devcontainer/scripts/runtime-supervisor.py:1074`.

A failed bootstrap, configuration check, core phase, or core service latches the
runtime with PID 1 running; the container exits nonzero only when the controller
or supervisord fails — `.devcontainer/scripts/runtime-supervisor.py:890`. The
Dev Container profile instead exits on a latch, so the editor sees the failure.

## Guarantees

- Release binaries are pinned by version and checksum, the catalog and validator
  by verified version args. Apt packages are not pinned: they are whatever the
  enabled repositories served at build time.
- The firewall is installed but inert; enabling it default-DROPs IPv4 egress
  outside the allowlist and blocks IPv6 entirely.
- The catalog staged in the image changes only with a new image.
- `agentdev-deploy` never fetches, pulls, resets, or switches branches in a
  reused workspace and never changes a bind checkout's ownership.
