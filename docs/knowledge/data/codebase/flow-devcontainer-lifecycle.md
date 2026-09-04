---
type: codebase
description: 'From opening the folder to a working session: host init, Compose, the three lifecycle hooks, and the web-only session hook.'
source:
- .devcontainer
- docker/desktop
- .agents/plugins/agentdev/hooks
source_digest: sha256:e147b7e7a74574487caf97238d136336271c5cf5ace917bb9438d75f8d05aa34
verified:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
stale_after: 2026-12-03
generated:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
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
   `.devcontainer/.env`, creates the shared `agentdev-agents-auth` volume —
   `.devcontainer/devcontainer.json:3`,
   `.devcontainer/devcontainer-init.sh:21-27`
2. Compose starts the `devcontainer` service from the digest-pinned image,
   layering `devcontainer-compose-pins.yml` over `docker-compose.yml`, and the
   `mcp-gateway` sidecar when the `mcp` profile was written to `.env` —
   `.devcontainer/devcontainer.json:7`, `.devcontainer/docker-compose.yml:2,53`
3. `postCreateCommand` (once per instance): ownership fixes, the
   `~/.claude.json` symlink into the `agentdev-claude` volume,
   `codebase-memory-mcp install`, auth directories and the Codex auth link,
   `uv sync`, then the image-staged catalog installed for Codex and for Claude
   at user scope — `.devcontainer/scripts/postCreateCommand.sh:56-91`, in
   [lifecycle scripts](devcontainer/scripts.md)
4. `postStartCommand` (every start): CBM daemon and index, git `safe.directory`,
   pre-commit hooks, keyring, the firewall gate, Xpra in the background —
   `.devcontainer/scripts/postStartCommand.sh:9-25`
5. `postAttachCommand` (every editor attach): CBM index, `uv sync`, and the
   catalog reinstalled from this checkout at local scope, which is how the
   catalog is developed in place —
   `.devcontainer/scripts/postAttachCommand.sh:8-15`
6. In the Claude Code web environment only, the plugin's `SessionStart` hook
   runs `devcontainer up`, which replays steps 1–5 —
   `.agents/plugins/agentdev/hooks/session-start.sh:5,29`

## Failure modes

- Step 3 is shadowed by design: the build-time catalog install under `~/.claude`
  is hidden by the volume mount, so a container that skips the hooks resolves
  the image's copy and a devcontainer resolves the hook's.
- `CBM_CACHE_DIR` unset aborts steps 3–5 at the first CBM script; a missing
  `codebase-memory-mcp` binary is skipped instead.
- `ENABLE_FIREWALL=true` in an image built without the firewall role fails step
  4.
- A CI `container:` job supplies none of `containerEnv` or the mounts;
  `ci-hooks-repro.sh` reproduces that environment locally.
- `AGENTDEV_SKIP_PRE_COMMIT` and `AGENTDEV_SKIP_XPRA` are the documented
  opt-outs for callers that never commit or never attach a desktop.
