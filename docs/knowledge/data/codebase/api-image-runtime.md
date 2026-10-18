---
type: codebase
description: 'What a consumer of ghcr.io/plume-works/agent-desktop and agent-opencode can rely on: environment variables each image reads, files and tools it provides, labels, ports, and, for agent-opencode, its entrypoint, health, and volumes.'
source:
- docker
- ansible/roles/agentic_tools
- ansible/roles/devcontainer_firewall
- compose.opencode.yml
source_digest: sha256:6b6012f7ca4f5776d7af4861ad6337344b31e062d7da30703cdb87f5ff646ab8
verified:
  by: claude-code/opus-5.5
  at: 2026-10-18T18:45:54Z
stale_after: 2027-01-16
generated:
  by: claude-code/opus-5.5
  at: 2026-10-18T18:45:54Z
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
- Labels `org.opencontainers.image.version.agentdev` and
  `org.opencontainers.image.version.validate-agent-files` —
  `docker/desktop/agent-desktop.Dockerfile:70-71`

## Environment the image reads

| Variable                                            | Read by                                                               | Meaning                                                                  |
| --------------------------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `DEV_WORKSPACE_FOLDER`                              | firewall allowlist lookup, lifecycle scripts                          | the mounted workspace; falls back to the baked `WORKSPACE_FOLDER`        |
| `ENABLE_FIREWALL`                                   | `.devcontainer/scripts/firewall.sh`                                   | `true` applies `init-firewall.sh`; anything else leaves it inert         |
| `FIREWALL_ALLOWLIST`                                | `init-firewall.sh:14`                                                 | overrides the allowlist path                                             |
| `XPRA_HOST`, `XPRA_VIDEO_ENCODERS`, `XPRA_LOG_FILE` | `/start-xpra.sh:6-14`                                                 | bind host, encoders, log path                                            |
| `AGENTDEV_CATALOG_DIR`                              | set by the image (`Dockerfile:68`), read by `postCreateCommand.sh:69` | where the catalog is staged (`/opt/agentdev`)                            |
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
  `ninja`, `shellcheck`, `zizmor`, `jq`, `iwe`/`iwes`, `codebase-memory-mcp`,
  `validate_agent_files`, `pre-commit`, `xpra`, `gnome-keyring-daemon`, Docker
  CE with buildx and compose
- `EXPOSE 14500` — the Xpra HTML5 container port, fixed by default and
  overridable with `/start-xpra.sh --port`; the devcontainer forwards `14500`

## agent-opencode

The image runs itself:
`ENTRYPOINT ["/opt/agentdev-runtime/runtime-supervisor.py", "run"]`,
`EXPOSE 4096 14500`, and a `HEALTHCHECK` that passes once every required service
is ready — `docker/opencode/agent-opencode.Dockerfile:59-65`. It must run
privileged, with volumes at `/home/agent`, `/uv`, `/var/lib/docker`,
`/workspaces/project` (or a bind checkout), and `/var/lib/agentdev/auth`; the
supported deployment is the root `compose.opencode.yml`.

| Variable                                                                                                                                                                   | Meaning                                                                                                                   |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `OPENCODE_SERVER_PASSWORD`                                                                                                                                                 | required, nonempty; OpenCode listens on `0.0.0.0:4096` behind it                                                          |
| `AGENTDEV_UID`, `AGENTDEV_GID`                                                                                                                                             | numeric runtime identity, default `1000`; must match within one auth-volume cohort                                        |
| `AGENTDEV_REPOSITORY_URL`, `AGENTDEV_REPOSITORY_REF`                                                                                                                       | clone an empty workspace once, optionally at a branch or tag                                                              |
| `GH_TOKEN`, `GITHUB_TOKEN`                                                                                                                                                 | HTTPS Git through `gh`, configured before a clone; never written to disk                                                  |
| `AGENTDEV_SKIP_XPRA`                                                                                                                                                       | nonempty drops the desktop from startup and readiness                                                                     |
| `ENABLE_FIREWALL`, `AGENTDEV_TRUSTED_PROXY_CIDRS`, `FIREWALL_ALLOWLIST`                                                                                                    | opt-in egress firewall; proxy sources allowed to 4096/14500; allowlist override of `/etc/agentdev/firewall-allowlist.txt` |
| `AGENTDEV_RECOVERY_ATTEMPTS`, `AGENTDEV_RECOVERY_BACKOFF`, `AGENTDEV_HEALTHY_RESET`, `AGENTDEV_SERVICE_START_TIMEOUT`, `AGENTDEV_PREPARE_TIMEOUT`, `AGENTDEV_STOP_TIMEOUT` | recovery budget (3, doubling from 1 s, reset after 60 s healthy), deadlines (60 s, 1800 s, 30 s)                          |

Xpra on `14500` has no password. `docker exec` sessions see the same `DISPLAY`,
`DOCKER_HOST`, `XDG_RUNTIME_DIR`, and `DBUS_SESSION_BUS_ADDRESS` as OpenCode's
tools. `/run/agentdev/failed` holds the reason after a terminal failure, and the
container then exits `1`.

## Guarantees

- Release binaries are pinned by version and checksum, the catalog and validator
  by verified version args. Apt packages are not pinned: they are whatever the
  enabled repositories served at build time.
- The firewall is installed but inert; enabling it default-DROPs IPv4 egress
  outside the allowlist and blocks IPv6 entirely.
- The catalog staged in the image changes only with a new image.
- `agent-opencode` never fetches, pulls, resets, or switches branches in a
  reused workspace and never changes a bind checkout's ownership.
