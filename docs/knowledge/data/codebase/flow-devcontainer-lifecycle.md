---
type: codebase
description: 'From opening the folder to a working session: host init, Compose, the image''s supervised services, and its create, start, and attach commands.'
source:
- .devcontainer
- docker/devcontainer
- py_packages/agentdev_runtime
source_digest: sha256:a6792e1d74cb875936cc8fafcc14c55f7d5b30ff208bdae52c6dfcf10e55bca7
verified:
  by: claude-code/opus-5.5
  at: 2026-10-31T16:27:53Z
stale_after: 2027-01-29
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T16:27:53Z
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
   `docker/devcontainer/agentdev-devcontainer.Dockerfile:38-47`
3. PID 1 is `agentdev-runtime supervisor run` in the `devcontainer` profile: the
   root bootstrap checks the installed `agentdev_runtime` distribution against
   its `RECORD` and accepts the mounted account and workspace, then supervisord
   starts D-Bus, keyring, Docker, CBM, and Xpra as core services and publishes
   readiness in `/run/agentdev/state.json` once their probes pass —
   `py_packages/agentdev_runtime/agentdev_runtime/supervisor.py:894`,
   `py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py:314`, in the
   [agentdev_runtime package](py_packages/agentdev_runtime.md)
4. `postCreateCommand`, `agentdev-runtime lifecycle created` (once per
   container): ancestor and mount ownership, `safe.directory`, then
   `agentdev-runtime state create` — the `~/.claude.json` symlink into the
   `agentdev-claude` volume, the CBM agent wiring (a failure only warns), auth
   directories, Claude first-run pre-approval unless
   `AGENTDEV_SKIP_CLAUDE_PREAPPROVE` is set, and the Codex auth link — uv sync
   and pre-commit hooks for present configuration, and the image-staged
   catalog's install; then the image's `created` hooks and the create marker,
   which releases the opt-in OpenCode and Remote Control programs —
   `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py:76`
5. `postStartCommand`, `agentdev-runtime lifecycle ready` (every start, and the
   `waitFor` target): wait until `agentdev-runtime health ready` passes, failing
   when the runtime failed or is late; then `safe.directory`, the gh git
   credential helper, the Codex auth link, the agent policies, and the `started`
   hooks — `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py:141`. In
   Coder, the template's `coder_script` on the dev container's sub-agent runs
   `agentdev-runtime coder start` after the agent starts, which prunes unused
   images in the nested Docker engine, repeats the gh helper setup with the
   agent's environment, starts the OpenCode web UI on `tmux -L opencode`, then
   execs `agentdev-runtime remote-control start` —
   `py_packages/agentdev_runtime/agentdev_runtime/coder.py:22`
6. `postAttachCommand`, `agentdev-runtime lifecycle attached` (every editor
   attach): a background CBM index request, uv sync, and, only when the checkout
   carries the complete catalog, its catalog install at local scope, with
   OpenCode's bridge entry repointed at it, which is how this repository
   develops the catalog in place; then the `attached` hooks —
   `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py:158`

## Failure modes

- The build-time catalog install under `~/.claude` is hidden by the volume
  mount, so a container that runs no lifecycle resolves the image's copy and a
  Dev Container resolves the one step 4 installs.
- A required service that exhausts recovery withdraws readiness; the
  devcontainer profile then exits nonzero, and step 5 fails naming the runtime
  state, so the editor never attaches to a partial runtime.
- An installed package file changed, added, or removed fails step 3.
- `CBM_CACHE_DIR` unset aborts the first CBM step; a missing
  `codebase-memory-mcp` binary is skipped instead. Any other step 4 failure ends
  the create phase; a failed CBM install only warns.
- `ENABLE_FIREWALL=true` in an image built without the firewall role fails the
  bootstrap.
- A CI `container:` job runs no image lifecycle and no supervisor; it runs
  `agentdev-runtime lifecycle created`, `ready --no-wait`, and `attached`, and
  `ready --no-wait` starts only the CBM daemon before the per-start repairs.
- `AGENTDEV_SKIP_PRE_COMMIT`, `AGENTDEV_SKIP_XPRA`, and
  `AGENTDEV_SKIP_CLAUDE_PREAPPROVE` are the documented opt-outs for callers that
  never commit, never attach a desktop, or must not enable project MCP servers.
- Remote Control stays down when `claude auth status` reports no live claude.ai
  login; a setup token alone does not start it. Running
  `agentdev-runtime remote-control start` by hand from a Coder terminal after
  `/login` starts it on the `tmux -L claude-remote` server. Outside Coder, the
  supervised `remote-control` program starts it when `AGENTDEV_CLAUDE_RC_MODE`
  is set.
