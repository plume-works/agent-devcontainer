---
type: codebase
description: 'From opening the folder to a working session: host init, Compose, and the three lifecycle hooks.'
source:
- .devcontainer
- docker/desktop
source_digest: sha256:b06176bf7acf8e6ec14fd859b4ccfc6e791ece003e4b937b26fef302e2c9953b
verified:
  by: claude-code/opus-5.5
  at: 2026-10-19T16:30:00Z
stale_after: 2027-01-17
generated:
  by: claude-code/opus-5.5
  at: 2026-10-19T16:30:00Z
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
3. `postCreateCommand` (once per instance): ownership fixes, then
   `setup-agent-state.sh create`: the `~/.claude.json` symlink into the
   `agentdev-claude` volume, `codebase-memory-mcp install` (a failure only
   warns), auth directories, Claude first-run pre-approval unless
   `AGENTDEV_SKIP_CLAUDE_PREAPPROVE` is set, and the Codex auth link. Then
   `uv sync`, then `setup-agent-state.sh catalog` installs the image-staged
   catalog for Codex (with its agents), for Claude at user scope, and as
   OpenCode's bridge plugin —
   `.devcontainer/scripts/postCreateCommand.sh:56-73`, in [lifecycle
   scripts](devcontainer/scripts.md)
4. `postStartCommand` (every start): CBM daemon and index, git `safe.directory`,
   pre-commit hooks, keyring, the gh git credential helper, the firewall gate,
   Xpra in the background, `setup-agent-state.sh links` for the Codex auth link,
   then `agent-policy` for both agents' full-access policies in their user
   configuration files — `.devcontainer/scripts/postStartCommand.sh:9-30`. The
   gh helper setup there sees only a login stored on disk or in the keyring.
   Claude Remote Control is not part of it: in Coder, the template's
   `coder_script` on the dev container's sub-agent runs `coder-agent-start.sh`
   after the agent starts, which prunes unused images in the nested Docker
   engine, repeats the gh helper setup with the agent's environment, starts the
   OpenCode web UI on `tmux -L opencode`, then execs
   `claude-remote-control-start.sh` —
   `.devcontainer/scripts/coder-agent-start.sh:9-21`
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
- Remote Control stays down when `claude auth status` reports no live claude.ai
  login; a setup token alone does not start it. Running
  `claude-remote-control-start.sh` by hand from a Coder terminal after `/login`
  starts it on the `tmux -L claude-remote` server. Outside Coder nothing starts
  it.
