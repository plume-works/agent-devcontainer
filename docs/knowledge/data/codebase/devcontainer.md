---
type: codebase
description: 'The template surface a consuming project copies: devcontainer.json, the Compose stack with its MCP gateway sidecar, the host-side init script, the digest pin, and the firewall allowlist.'
source:
- .devcontainer
- devcontainer-compose-pins.yml
source_digest: sha256:8ef26c0aabf4da552bb4c5aab83b0af19670d7ce4b0f946f611c724f08cb611c
verified:
  by: claude-code/opus-5
  at: 2026-09-05T17:42:42Z
stale_after: 2026-12-04
generated:
  by: claude-code/opus-5
  at: 2026-09-05T17:42:42Z
sources:
- id: code
  resource: .devcontainer
---

# Devcontainer scaffolding

What turns the published image into a working editor container. It is the
surface `/agentdev:template-consume` copies into another repository, so
everything here must work with only `DEV_WORKSPACE_FOLDER` set and the image
pulled.

## Contains

[Lifecycle scripts](devcontainer/scripts.md)

## Public surface

- `.devcontainer/devcontainer.json` — `initializeCommand:3`, the layered
  `dockerComposeFile:7`, `containerEnv` (`ENABLE_FIREWALL`, `DISPLAY`,
  `DEVCONTAINER_ID`, `DEV_WORKSPACE_FOLDER`, `CLAUDE_SECURESTORAGE_CONFIG_DIR`,
  `CBM_CACHE_DIR`, `PRE_COMMIT_HOME`, `UV_*`), the Xpra `forwardPorts` and
  `portsAttributes` block (`:51-57`), four named volume mounts (`:58-102`), the
  VS Code extension and settings block, and the three lifecycle commands
  (`:253-256`)
- `.devcontainer/docker-compose.yml` — the `mcp-gateway` sidecar (`:2`, profile
  `mcp`) and the privileged `devcontainer` service (`:53`) with the shared
  `agentdev-agents-auth` volume (`:99-103`)
- `devcontainer-compose-pins.yml` — the digest pin Renovate advances
- `.devcontainer/firewall-allowlist.txt` — read by the firewall at start

## How it works

`devcontainer-init.sh` runs on the host before Compose: it writes
`.devcontainer/.env` with the git common dir, the workspace path and basename,
and the host MCP directory and secrets socket when Docker Desktop provides them
(stubs otherwise), and creates the `agentdev-agents-auth` volume Compose
declares as external. Compose then layers the tag-only `docker-compose.yml`
under the digest pin, mounts the workspace at `/workspaces/<basename>` and the
git common dir at its host path so worktrees resolve, and starts the MCP gateway
only when the `mcp` profile was activated. Per-instance state (`~/.claude`,
`~/.codex`, `/uv`, `.cache`) is on Compose-scoped volumes; only credentials
share the literal `agentdev-agents-auth` volume across instances.

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
  `postCreateCommand`.
- The MCP gateway publishes no host port and runs `--allow-unauthenticated` on
  the private Compose network; both are what let several worktrees run at once.
- `initializeCommand` runs under `/bin/sh -c` with no `HOME` in Codespaces; the
  script defaults `HOME` to empty so the host probes fall through.

## Key references

Verified anchor points (line numbers as of 2026-09-05):

- `.devcontainer/devcontainer.json:3,7` — init command, layered compose files
- `.devcontainer/devcontainer.json:51-57` — Xpra port forwarding
- `.devcontainer/devcontainer.json:58-102` — the four volume mounts
- `.devcontainer/devcontainer.json:253-256` — lifecycle commands
- `.devcontainer/docker-compose.yml:2,53,103` — sidecar, service, volumes
- `.devcontainer/devcontainer-init.sh:9` — `HOME` default for Codespaces
- `devcontainer-compose-pins.yml:14` — the digest pin
