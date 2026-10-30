---
type: codebase
description: 'The template surface a consuming project copies: devcontainer.json, the Compose stack with its MCP gateway sidecar, the host-side init script, the digest pin, and the firewall allowlist.'
source:
- .devcontainer
- devcontainer-compose-pins.yml
source_digest: sha256:301e8e86d422f75f38b5b1dde6fd6cde0df854bae41c408846328bff4a1c0226
verified:
  by: claude-code/opus-5.5
  at: 2026-10-30T01:00:00Z
stale_after: 2027-01-28
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T01:00:00Z
sources:
- id: code
  resource: .devcontainer
---

# Devcontainer scaffolding

This repository's descriptor for the published `agentdev-devcontainer` image:
the workspace, mounts, sidecar, editor settings, and pin. The image's
`devcontainer.metadata` supplies the lifecycle commands, `waitFor`, privileged
mode, and nested-Docker storage, so the descriptor declares none of them. The
descriptor files are the surface `/agentdev:template-consume` keeps in another
repository.

## Contains

[Lifecycle scripts](devcontainer/scripts.md)

## Public surface

- `.devcontainer/devcontainer.json` — `initializeCommand:3`, the layered
  `dockerComposeFile:7`, the SSH Feature (`:15`), `containerEnv`
  (`ENABLE_FIREWALL`, `DEVCONTAINER_ID`, `DEV_WORKSPACE_FOLDER`, `EXPO_TOKEN`,
  `CLAUDE_SECURESTORAGE_CONFIG_DIR`, `CBM_CACHE_DIR`, `PRE_COMMIT_HOME`,
  `UV_*`), the Xpra `forwardPorts` and `portsAttributes` block (`:53-59`), six
  named volume mounts (`:60-119`), and the VS Code extension and settings block
- `.devcontainer/docker-compose.yml` — the `mcp-gateway` sidecar (`:2`, profile
  `mcp`) and the privileged `devcontainer` service (`:53`) with its
  launcher-derived `hostname` (`:59`), the pass-through `GIT_*` identity
  variables (`:70-73`), and the shared `agentdev-agents-auth` volume (`:104`)
- `devcontainer-compose-pins.yml` — the `agentdev-devcontainer` tag-and-digest
  pin Renovate advances, shared with every workflow `container.image`
- `.devcontainer/firewall-allowlist.txt` — read by the firewall at start, and
  baked by both runtime images as their default allowlist
- `.devcontainer/.agent.metadata.json` — masks the feature version pins, and the
  versions and digests `devcontainer-lock.json` records for them, out of this
  directory's map digest; see architecture/agent-metadata-files

## How it works

`devcontainer-init.sh` runs on the host before Compose: it writes
`.devcontainer/.env` with the git common dir, the workspace path and basename,
the container hostname `scripts/container-hostname.sh` derives from the
launcher, and the host MCP directory and secrets socket when Docker Desktop
provides them (stubs otherwise), and creates the `agentdev-agents-auth` volume
Compose declares as external. Compose then layers the tag-only
`docker-compose.yml` under the digest pin, mounts the workspace at
`/workspaces/<basename>` and the git common dir at its host path so worktrees
resolve, and starts the MCP gateway only when the `mcp` profile was activated.
Per-instance state (`~/.claude`, `~/.codex`, `~/.local/share/opencode`, `/uv`,
`.cache`, and the sibling checkout at `/workspaces/project`) is on
Compose-scoped volumes; only Claude and Codex credentials share the literal
`agentdev-agents-auth` volume across instances. The `devcontainer` service has
no `command` or `init`: the image's supervisor is PID 1, owns the persistent
services, and reaps orphans. The image's create, start, and attach commands then
run the [lifecycle scripts](devcontainer/scripts.md) baked at
`/opt/agentdev-runtime`; the start phase also restores Codex and OpenCode
full-access policies in their user configuration files.

Both runtime images bake `scripts/` at `/opt/agentdev-runtime`; this directory's
Compose and `devcontainer.json` reach only `agentdev-devcontainer`.
`agentdev-deploy`'s deployment is the root `compose.opencode.yml`.

## Depends on

The [image runtime contract](api-image-runtime.md) — the env variables and
scripts it reads exist because the image provides them. [Renovate](github.md)
moves the digest pin.

## Invariants & gotchas

- The digest pin lives at the repository root, not under `.devcontainer/`, so a
  pin bump does not match the CI image path filter and retrigger the build that
  produced it.
- `~/.claude.json` is a file; Docker volumes are directories, so the file is
  persisted inside the `agentdev-claude` volume and symlinked by
  `setup-agent-state.sh create`, which the image's create command runs.
- Declaring lifecycle commands or the Docker-in-Docker Feature here as well
  would run each phase twice and start a second Docker engine.
- The MCP gateway publishes no host port and runs `--allow-unauthenticated` on
  the private Compose network; both are what let several worktrees run at once.
- `initializeCommand` runs under `/bin/sh -c` with no `HOME` in Codespaces; the
  script defaults `HOME` to empty so the host probes fall through.
- Claude Remote Control names its environment after the container hostname, so
  the `hostname` Compose sets is what Claude Desktop shows; without the init
  script it falls back to `agentdev`.
- The `GIT_*` identity entries carry no value, so an unset host variable stays
  unset in the container; an empty value would override `user.name`.
- No credential enters through Compose; a login is made inside a container and
  persists in the shared volume.

## Key references

Verified anchor points (line numbers as of 2026-10-29):

- `.devcontainer/devcontainer.json:3,7` — init command, layered compose files
- `.devcontainer/devcontainer.json:15` — the SSH Feature, the only Feature
- `.devcontainer/devcontainer.json:53-59` — Xpra port forwarding
- `.devcontainer/devcontainer.json:60-119` — the six volume mounts
- `.devcontainer/docker-compose.yml:2,53,106` — sidecar, service, volumes
- `.devcontainer/docker-compose.yml:59` — launcher-derived hostname
- `.devcontainer/docker-compose.yml:70-73,104` — identity pass-through, shared
  auth volume
- `docker/devcontainer/agentdev-devcontainer.Dockerfile:41-50` — the lifecycle
  the descriptor inherits
- `.devcontainer/devcontainer-init.sh:11` — `HOME` default for Codespaces
- `.devcontainer/devcontainer-init.sh:24` — shared auth volume creation
- `.devcontainer/devcontainer-init.sh:30,38` — `CONTAINER_HOSTNAME` written to
  `.env`
- `devcontainer-compose-pins.yml:14` — the digest pin
