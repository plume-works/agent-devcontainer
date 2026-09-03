---
type: codebase
description: 'What a consumer of ghcr.io/plume-works/agent-desktop can rely on: environment variables the image reads, files and tools it provides, labels, and the port it exposes.'
source:
- docker
- ansible/roles/agentic_tools
- ansible/roles/devcontainer_firewall
commit: eb60f60450c6009b076bc51993b49a924653eaa4
verified:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:09:00Z
stale_after: 2026-12-02
generated:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:09:00Z
sources:
- id: code
  resource: docker
  title: the code this map describes, read at commit eb60f60
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
- Labels `org.opencontainers.image.version.agentdev` and
  `org.opencontainers.image.version.validate-agent-files` —
  `docker/desktop/agent-desktop.Dockerfile:70-71`

## Environment the image reads

| Variable                                            | Read by                                                               | Meaning                                                                  |
| --------------------------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `DEV_WORKSPACE_FOLDER`                              | firewall allowlist lookup, lifecycle scripts                          | the mounted workspace; falls back to the baked `WORKSPACE_FOLDER`        |
| `ENABLE_FIREWALL`                                   | `.devcontainer/scripts/firewall.sh`                                   | `true` applies `init-firewall.sh`; anything else leaves it inert         |
| `FIREWALL_ALLOWLIST`                                | `init-firewall.sh:14`                                                 | overrides the allowlist path                                             |
| `DEVCONTAINER_ID`                                   | `/start-xpra.sh:188-190`                                              | derives the Xpra port `14500 + cksum % 100`                              |
| `XPRA_HOST`, `XPRA_VIDEO_ENCODERS`, `XPRA_LOG_FILE` | `/start-xpra.sh:6-13`                                                 | bind host, encoders, log path                                            |
| `AGENTDEV_CATALOG_DIR`                              | set by the image (`Dockerfile:68`), read by `postCreateCommand.sh:89` | where the catalog is staged (`/opt/agentdev`)                            |
| `CBM_CACHE_DIR`                                     | the `codebase-memory-mcp-*.sh` scripts                                | required; cache and logs location                                        |
| `AGENTDEV_SKIP_PRE_COMMIT`, `AGENTDEV_SKIP_XPRA`    | `postStartCommand.sh` and `setup-pre-commit.sh`                       | opt out of hook install and desktop start                                |
| `GH_TOKEN` / `GITHUB_TOKEN`, `VERBOSE_GH`           | the `gh` wrapper                                                      | an explicit token wins; otherwise derived from the git credential helper |

## Files and tools

- `/entrypoint.sh` (`exec "$@"`), `/start-xpra.sh`,
  `/usr/local/bin/init-firewall.sh` with a NOPASSWD sudoers entry, the `gh`
  wrapper ahead of the real `gh`
- `/opt/agentdev` — the staged catalog, root-owned and read-only, with the
  plugin already installed for both agents at build time
- On `PATH`: `uv`, `bun`, `node`, `claude`, `codex`, `gh`, `cmake`, `ninja`,
  `shellcheck`, `zizmor`, `jq`, `iwe`/`iwes`/`iwec`, `codebase-memory-mcp`,
  `validate_agent_files`, `pre-commit`, `xpra`, `gnome-keyring-daemon`, Docker
  CE with buildx and compose
- `EXPOSE 14500` — the Xpra HTML5 base port; the devcontainer forwards
  `14500-14599`

## Guarantees

- Everything installed is pinned: apt from fixed repositories, release binaries
  by version and checksum, Xpra by tag, the catalog and validator by verified
  version args.
- The firewall is installed but inert; enabling it default-DROPs IPv4 egress
  outside the allowlist and blocks IPv6 entirely.
- The catalog staged in the image changes only with a new image.
