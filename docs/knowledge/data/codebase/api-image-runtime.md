---
type: codebase
description: 'What a consumer of ghcr.io/plume-works/agent-desktop and agent-opencode can rely on: environment variables each image reads, files and tools it provides, labels, ports, and, for agent-opencode, its entrypoint, health, and volumes.'
source:
- docker
- ansible/roles/agentic_tools
- ansible/roles/devcontainer_firewall
- compose.opencode.yml
source_digest: sha256:f75ba4ca4eeeb7638c9a050f2d43dc8df9d398a0cb5fc0eaf463b6c86a679fee
verified:
  by: claude-code/opus-5.5
  at: 2026-10-23T21:51:57Z
stale_after: 2027-01-21
generated:
  by: claude-code/opus-5.5
  at: 2026-10-23T21:51:57Z
sources:
- id: code
  resource: docker
---

# Interface: image runtime contract

The published image is consumed by this repository's devcontainer, by
Codespaces, and by any project pointing its own `devcontainer.json` at it. This
is the surface those consumers touch; the build that produces it is
[docker/](docker.md) plus [ansible/](ansible.md).

## Images

- `ghcr.io/plume-works/agent-desktop:edge` — pinned by digest in
  `devcontainer-compose-pins.yml`; multi-arch `linux/amd64` + `linux/arm64`
- `ghcr.io/plume-works/ubuntu-ansible:edge` — the base it is built from
- `ghcr.io/plume-works/agent-opencode:edge` — the standalone runtime, built on
  the same run's `agent-desktop` digest and pinned in
  `opencode-compose-pins.yml`; multi-arch, labelled
  `org.opencontainers.image.base.name` with that digest —
  `docker/opencode/agent-opencode.Dockerfile:3-7`
- Labels `org.opencontainers.image.version.agentdev`,
  `org.opencontainers.image.version.playwright`, and
  `org.opencontainers.image.version.validate-agent-files` —
  `docker/desktop/agent-desktop.Dockerfile:77-79`

## Environment the image reads

| Variable                                            | Read by                                                               | Meaning                                                                  |
| --------------------------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `DEV_WORKSPACE_FOLDER`                              | firewall allowlist lookup, lifecycle scripts                          | the mounted workspace; falls back to the baked `WORKSPACE_FOLDER`        |
| `ENABLE_FIREWALL`                                   | `.devcontainer/scripts/firewall.sh`                                   | `true` applies `init-firewall.sh`; anything else leaves it inert         |
| `FIREWALL_ALLOWLIST`                                | `init-firewall.sh:14`                                                 | overrides the allowlist path                                             |
| `XPRA_HOST`, `XPRA_VIDEO_ENCODERS`, `XPRA_LOG_FILE` | `/start-xpra.sh:6-14`                                                 | bind host, encoders, log path                                            |
| `XPRA_PASSWORD`                                     | `/start-xpra.sh:285-287`                                              | nonempty: every TCP/WebSocket session must authenticate with it          |
| `AGENTDEV_CATALOG_DIR`                              | set by the image (`Dockerfile:68`), read by `postCreateCommand.sh:69` | where the catalog is staged (`/opt/agentdev`)                            |
| `PLAYWRIGHT_BROWSERS_PATH`                          | set by the image                                                      | shared, runtime-writable browser binaries at `/opt/playwright`           |
| `CBM_CACHE_DIR`                                     | the `codebase-memory-mcp-*.sh` scripts                                | required; cache and logs location                                        |
| `AGENTDEV_SKIP_PRE_COMMIT`, `AGENTDEV_SKIP_XPRA`    | `postStartCommand.sh` and `setup-pre-commit.sh`                       | opt out of hook install and desktop start                                |
| `GH_TOKEN` / `GITHUB_TOKEN`, `VERBOSE_GH`           | the `gh` wrapper                                                      | an explicit token wins; otherwise derived from the git credential helper |

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

## agent-opencode

The image runs itself:
`ENTRYPOINT ["/opt/agentdev-runtime/runtime-supervisor.py", "run"]`,
`EXPOSE 4096 14500`, and a `HEALTHCHECK` of `runtime-health.sh ready` with a
10-minute start period — `docker/opencode/agent-opencode.Dockerfile:59-66`. It
must run privileged, with volumes at `/home/agent`, `/uv`, `/var/lib/docker`,
`/workspaces/project` (or a bind checkout), and `/var/lib/agentdev/auth`; the
supported deployment is the root `compose.opencode.yml`.

| Variable                                                                                | Meaning                                                                                                                   |
| --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `OPENCODE_SERVER_PASSWORD`                                                              | required, nonempty; OpenCode listens on `0.0.0.0:4096` behind it                                                          |
| `AGENTDEV_UID`, `AGENTDEV_GID`                                                          | numeric runtime identity, default `1000`; must match within one auth-volume cohort                                        |
| `AGENTDEV_REPOSITORY_URL`, `AGENTDEV_REPOSITORY_REF`                                    | clone an empty workspace once, optionally at a branch or tag                                                              |
| `GH_TOKEN`, `GITHUB_TOKEN`                                                              | HTTPS Git through `gh`, configured before a clone; never written to disk                                                  |
| `XPRA_PASSWORD`                                                                         | required, nonempty, unless `AGENTDEV_SKIP_XPRA` is true; Xpra's session password, separate from OpenCode's                |
| `AGENTDEV_SKIP_XPRA`, `AGENTDEV_STRICT_STARTUP`                                         | booleans: `1`/`true`/`yes`/`on` or `0`/`false`/`no`/`off`/empty, any case; strict makes every optional failure latch      |
| `ENABLE_FIREWALL`, `AGENTDEV_TRUSTED_PROXY_CIDRS`, `FIREWALL_ALLOWLIST`                 | opt-in egress firewall; proxy sources allowed to 4096/14500; allowlist override of `/etc/agentdev/firewall-allowlist.txt` |
| `AGENTDEV_RECOVERY_ATTEMPTS`, `AGENTDEV_PROBE_FAILURES`, `AGENTDEV_STOP_TIMEOUT`        | positive integers: 3 attempts, 2 failed probes, 30 s stop                                                                 |
| `AGENTDEV_RECOVERY_BACKOFF`, `AGENTDEV_HEALTHY_RESET`, `AGENTDEV_SERVICE_START_TIMEOUT` | positive seconds: backoff doubling from 1, reset after 60 healthy, 60 to first readiness                                  |
| `AGENTDEV_BOOTSTRAP_TIMEOUT`, `AGENTDEV_PREPARE_TIMEOUT`, `AGENTDEV_HEALTH_INTERVAL`    | positive seconds: 1800 for the bootstrap, 1800 per preparation step, 2 between controller checks                          |

Any other spelling or a non-positive value latches a configuration failure
naming the variable — `.devcontainer/scripts/runtime-supervisor.py:77`, `:136`.
`docker exec` sessions see the same `DISPLAY`, `DOCKER_HOST`, `XDG_RUNTIME_DIR`,
and `DBUS_SESSION_BUS_ADDRESS` as OpenCode's tools.

Operator surface, all through `docker exec`:

- `/run/agentdev/state.json` — `state` (`pending`, `ready`, `degraded`,
  `failed`), `latched`, each component's `status` and `reason`, and a
  `heartbeat` refreshed every interval —
  `.devcontainer/scripts/runtime-supervisor.py:336`.
- `runtime-health.sh ready` passes only with a heartbeat under three intervals
  old, state `ready`, and passing `dbus`, `keyring`, and `opencode` probes;
  `runtime-health.sh status` prints the state, each failed or blocked component
  with its retry command, and the last failure —
  `.devcontainer/scripts/runtime-health.sh:48`, `:58`.
- `~/.local/state/agentdev/last-failure.json` on the home volume — startup ID,
  component, reason, command, exit status, at most 200 output lines, UTC time;
  only a later failure replaces it —
  `.devcontainer/scripts/runtime-supervisor.py:372`.
- `runtime-supervisor.py retry [component]` — resumes a latched runtime, or
  reruns one failed component, and exits `0` when it succeeded —
  `.devcontainer/scripts/runtime-supervisor.py:895`.

A failed bootstrap, configuration check, core phase, or core service latches the
runtime with PID 1 running; the container exits nonzero only when the controller
or supervisord fails — `.devcontainer/scripts/runtime-supervisor.py:740`.

## Guarantees

- Release binaries are pinned by version and checksum, the catalog and validator
  by verified version args. Apt packages are not pinned: they are whatever the
  enabled repositories served at build time.
- The firewall is installed but inert; enabling it default-DROPs IPv4 egress
  outside the allowlist and blocks IPv6 entirely.
- The catalog staged in the image changes only with a new image.
- `agent-opencode` never fetches, pulls, resets, or switches branches in a
  reused workspace and never changes a bind checkout's ownership.
