---
type: codebase
description: 'From opening the folder to a working session: host init, Compose, the image''s supervised services, and its create, start, and attach commands.'
source:
- .devcontainer
- docker/devcontainer
- docker/desktop
source_digest: sha256:11c7cf66416c02fa53aa953cb80f7a4c8fbd31bb76a0d183dc86fc3f7338841a
verified:
  by: claude-code/opus-5.5
  at: 2026-10-30T12:10:00Z
stale_after: 2027-01-28
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T12:10:00Z
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
   `.devcontainer/.env`, including the `CONTAINER_HOSTNAME` it derives from the
   launcher (Coder, VS Code, or the CLI), and creates the shared
   `agentdev-agents-auth` volume — `.devcontainer/devcontainer.json:3`,
   `.devcontainer/devcontainer-init.sh:13-53`
2. Compose starts the `devcontainer` service from the pinned
   `agentdev-devcontainer` image under that hostname, layering
   `devcontainer-compose-pins.yml` over `docker-compose.yml`, and the
   `mcp-gateway` sidecar when the `mcp` profile was written to `.env`. The Dev
   Containers tool merges the image's `devcontainer.metadata` — privileged mode,
   the kept entrypoint, the `/var/lib/docker` volume, and the three lifecycle
   commands — under the descriptor — `.devcontainer/devcontainer.json:7`,
   `.devcontainer/docker-compose.yml:2,53,59`,
   `docker/devcontainer/agentdev-devcontainer.Dockerfile:41-50`
3. PID 1 is `runtime-supervisor.py run` in the `devcontainer` profile: the root
   bootstrap checks `/opt/agentdev-runtime` against the image manifest and
   accepts the mounted account and workspace, then supervisord starts D-Bus,
   keyring, Docker, CBM, and Xpra as core services and publishes readiness in
   `/run/agentdev/state.json` once their probes pass —
   `.devcontainer/scripts/runtime-supervisor.py:966`,
   `.devcontainer/scripts/runtime-bootstrap.sh:190`, in [lifecycle
   scripts](devcontainer/scripts.md)
4. `postCreateCommand` (once per container): ancestor and mount ownership,
   `safe.directory`, then `setup-agent-state.sh create` — the `~/.claude.json`
   symlink into the `agentdev-claude` volume, `codebase-memory-mcp install` (a
   failure only warns), auth directories, Claude first-run pre-approval unless
   `AGENTDEV_SKIP_CLAUDE_PREAPPROVE` is set, and the Codex auth link — uv sync
   and pre-commit hooks for present configuration, and
   `setup-agent-state.sh catalog` for the image-staged catalog; then the image's
   `created` hooks and the create marker, which releases the opt-in OpenCode and
   Remote Control programs —
   `.devcontainer/scripts/devcontainer-created.sh:36-58`
5. `postStartCommand` (every start, and the `waitFor` target): wait until
   `runtime-health.sh ready` passes, failing when the runtime failed or is late;
   then `safe.directory`, the gh git credential helper,
   `setup-agent-state.sh links` and `agent-policy`, and the `started` hooks —
   `.devcontainer/scripts/devcontainer-ready.sh:20-46`. Claude Remote Control is
   not part of it: in Coder, the template's `coder_script` on the dev
   container's sub-agent runs `coder-agent-start.sh` after the agent starts,
   which prunes unused images in the nested Docker engine, repeats the gh helper
   setup with the agent's environment, starts the OpenCode web UI on
   `tmux -L opencode`, then execs `claude-remote-control-start.sh` —
   `.devcontainer/scripts/coder-agent-start.sh:9-21`
6. `postAttachCommand` (every editor attach): a background CBM index request, uv
   sync, and, only when the checkout carries the complete catalog,
   `setup-agent-state.sh catalog` for it at local scope, with OpenCode's bridge
   entry repointed at it, which is how this repository develops the catalog in
   place; then the `attached` hooks —
   `.devcontainer/scripts/devcontainer-attached.sh:15-24`

## Failure modes

- The build-time catalog install under `~/.claude` is hidden by the volume
  mount, so a container that runs no lifecycle resolves the image's copy and a
  Dev Container resolves the one step 4 installs.
- A required service that exhausts recovery withdraws readiness; the
  devcontainer profile then exits nonzero, and step 5 fails naming the runtime
  state, so the editor never attaches to a partial runtime.
- A file changed, added, or removed below `/opt/agentdev-runtime` fails step 3.
- `CBM_CACHE_DIR` unset aborts the first CBM script; a missing
  `codebase-memory-mcp` binary is skipped instead. Any other step 4 failure ends
  the create phase; a failed CBM install only warns.
- `ENABLE_FIREWALL=true` in an image built without the firewall role fails the
  bootstrap.
- A CI `container:` job runs no image lifecycle and no supervisor; it calls the
  checkout's `post*Command.sh` wrappers, whose start wrapper starts the services
  itself, and `ci-hooks-repro.sh` reproduces that environment locally.
- `AGENTDEV_SKIP_PRE_COMMIT`, `AGENTDEV_SKIP_XPRA`, and
  `AGENTDEV_SKIP_CLAUDE_PREAPPROVE` are the documented opt-outs for callers that
  never commit, never attach a desktop, or must not enable project MCP servers.
- Remote Control stays down when `claude auth status` reports no live claude.ai
  login; a setup token alone does not start it. Running
  `claude-remote-control-start.sh` by hand from a Coder terminal after `/login`
  starts it on the `tmux -L claude-remote` server. Outside Coder nothing starts
  it.
