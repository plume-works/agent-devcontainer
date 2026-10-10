---
type: codebase
description: 'From opening the folder to a working session: host init, Compose, and the three lifecycle hooks.'
source:
- .devcontainer
- docker/desktop
source_digest: sha256:1f1b9bf34b0d1037924134f0c88e8a0874e1db0591affe8bdbee83b6eaa6dd5c
verified:
  by: claude-code/opus-5.5
  at: 2026-10-10T01:20:00Z
stale_after: 2027-01-07
generated:
  by: claude-code/opus-5.5
  at: 2026-10-10T01:20:00Z
sources:
- id: code
  resource: .devcontainer
---

# Flow: devcontainer lifecycle

The order in which the [scaffolding](devcontainer.md) and the
[image](api-image-runtime.md) come together, and which step owns which piece of
state.

## Trace

1. `initializeCommand` runs `devcontainer-init.sh` on the host: writes
   `.devcontainer/.env` and creates the shared `agentdev-agents-auth` volume —
   `.devcontainer/devcontainer.json:3`,
   `.devcontainer/devcontainer-init.sh:13-35`
2. Compose starts the `devcontainer` service from the digest-pinned image,
   layering `devcontainer-compose-pins.yml` over `docker-compose.yml`, and the
   `mcp-gateway` sidecar when the `mcp` profile was written to `.env` —
   `.devcontainer/devcontainer.json:7`, `.devcontainer/docker-compose.yml:2,53`
3. `postCreateCommand` (once per instance): ownership fixes, the
   `~/.claude.json` symlink into the `agentdev-claude` volume,
   `codebase-memory-mcp install` (a failure only warns), auth directories,
   Claude first-run pre-approval unless `AGENTDEV_SKIP_CLAUDE_PREAPPROVE` is
   set, the Codex auth link, `uv sync`, then the image-staged catalog installed
   for Codex (with its agents), for Claude at user scope, and as OpenCode's
   bridge plugin — `.devcontainer/scripts/postCreateCommand.sh:56-98`, in
   [lifecycle scripts](devcontainer/scripts.md)
4. `postStartCommand` (every start): CBM daemon and index, git `safe.directory`,
   pre-commit hooks, keyring, the gh git credential helper, the firewall gate,
   Xpra in the background, Claude Remote Control under autostart with a
   claude.ai login, the Codex auth link, then Codex's full-access policy in
   `config.toml` — `.devcontainer/scripts/postStartCommand.sh:9-32`
5. `postAttachCommand` (every editor attach): CBM index, `uv sync`, and the
   catalog reinstalled from this checkout at local scope, with OpenCode's bridge
   entry repointed at it, which is how the catalog is developed in place —
   `.devcontainer/scripts/postAttachCommand.sh:8-16`

## Failure modes

- Step 3 is shadowed by design: the build-time catalog install under `~/.claude`
  is hidden by the volume mount, so a container that skips the hooks resolves
  the image's copy and a devcontainer resolves the hook's.
- `CBM_CACHE_DIR` unset aborts steps 4–5 at the first CBM script; a missing
  `codebase-memory-mcp` binary is skipped instead. Any other step 3 failure ends
  the lifecycle, so step 4 never runs; a failed CBM install only warns.
- `ENABLE_FIREWALL=true` in an image built without the firewall role fails step
  4\.
- A CI `container:` job supplies none of `containerEnv` or the mounts;
  `ci-hooks-repro.sh` reproduces that environment locally.
- `AGENTDEV_SKIP_PRE_COMMIT`, `AGENTDEV_SKIP_XPRA`, and
  `AGENTDEV_SKIP_CLAUDE_PREAPPROVE` are the documented opt-outs for callers that
  never commit, never attach a desktop, or must not enable project MCP servers.
- Remote Control stays down under autostart when `claude auth status` reports no
  live claude.ai login; a setup token alone does not start it. Running
  `claude-remote-control-start.sh` by hand after `/login` starts it.
