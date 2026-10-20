---
type: codebase
description: The postCreate, postStart, and postAttach hooks and the helpers they call — agent-state setup, catalog reinstalls, codebase-memory-mcp wiring, uv sync, keyring, firewall gate, auth links and full-access policies, gh credential helper, the Coder agent-start entry point, Remote Control, the OpenCode web UI — plus the standalone agent-opencode runtime built from the same helpers.
source: .devcontainer/scripts
source_digest: sha256:fad912d3fe01ca56c6d4881b025a0e9809adb51183fc8193401a8447322b0815
verified:
  by: claude-code/opus-5.5
  at: 2026-10-20T16:19:25Z
stale_after: 2027-01-18
generated:
  by: claude-code/opus-5.5
  at: 2026-10-20T05:05:29Z
sources:
- id: code
  resource: .devcontainer/scripts
---

# Devcontainer lifecycle scripts

Thirty-five shell scripts, all `set -euo pipefail` except the sourced
`runtime-paths.sh`, and four Python scripts. The three lifecycle commands in
[devcontainer.json](../devcontainer.md) fan out to them. The `agent-opencode`
image bakes the whole directory into `/opt/agentdev-runtime` and runs the
`runtime-*` scripts as its standalone lifecycle. Most scripts resolve the
workspace from `DEV_WORKSPACE_FOLDER`, with a `BASH_SOURCE` fallback.

## Public surface

Devcontainer lifecycle and shared helpers:

| Script                                                                               | Called by                            | Does                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------------------------------------------------------------------------------ | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `postCreateCommand.sh`                                                               | create (once)                        | ownership fixes, `setup-agent-state.sh create`, uv sync, `setup-agent-state.sh catalog <staged> user`                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `postStartCommand.sh`                                                                | every start                          | CBM daemon + index, git safe.directory, pre-commit hooks, keyring, gh helper, firewall gate, Xpra, `setup-agent-state.sh links`, then `agent-policy`                                                                                                                                                                                                                                                                                                                                                                                        |
| `postAttachCommand.sh`                                                               | every editor attach                  | CBM index, uv sync, reinstall the catalog from this checkout                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `setup-agent-state.sh create\|links\|agent-policy\|catalog <dir> [scope]`            | both hooks, standalone `prepare`     | `create`: register image user tooling (standalone), link `~/.claude.json` into the Claude dir, CBM install, auth dirs `0700`, Claude pre-approval, Codex auth link. `agent-policy`: both `configure-*.py`. `catalog`: the three reinstall scripts, scope to Claude only                                                                                                                                                                                                                                                                     |
| `runtime-paths.sh`                                                                   | sourced                              | the auth, Claude, Codex, and OpenCode roots, each `/root`-layout by default and overridable; `agentdev_standalone` reads `AGENTDEV_RUNTIME_MODE`                                                                                                                                                                                                                                                                                                                                                                                            |
| `reinstall-agentdev-claude.sh [root] [scope]`                                        | `catalog`, attach                    | remove stale marketplaces for `root`, add it, install every published plugin at `scope`                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `reinstall-agentdev-codex.sh [root]`                                                 | `catalog`, attach                    | the Codex equivalent, single-plugin; Codex has no scopes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `reinstall-agentdev-opencode.sh [root]`                                              | `catalog`, attach                    | point the `plugin` list of the user's `opencode.json` at `root`'s OpenCode bridge, replacing any earlier bridge entry                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `codebase-memory-mcp-{install,start,index}.sh`                                       | `create`, start, attach              | agent-config wiring, daemon start, repository index                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `repair-codex-cbm-hooks-block.py`                                                    | CBM install                          | move tables other than cbm's own hooks out of its `SessionStart` block in `${CODEX_HOME:-~/.codex}/config.toml`; no-op when nothing needs moving                                                                                                                                                                                                                                                                                                                                                                                            |
| `uv-sync.sh`                                                                         | create, attach, standalone           | drop a managed `.venv` link (not in standalone mode), `uv sync --all-groups --all-extras` into `/uv`                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `link-codex-auth.sh`                                                                 | `create`, `links`                    | move a regular credential file into its subdirectory of the shared auth root and symlink it back                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `configure-codex.py`                                                                 | `agent-policy`                       | set top-level `sandbox_mode` and `approval_policy` in `${CODEX_HOME:-~/.codex}/config.toml`, atomically at `0600`                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `configure-opencode.py`                                                              | `agent-policy`                       | merge the approved action and external-filesystem policy into the highest-precedence JSON or JSONC user config, atomically at `0600`                                                                                                                                                                                                                                                                                                                                                                                                        |
| `preapprove-claude-workspace.sh`                                                     | `create`                             | unless `AGENTDEV_SKIP_CLAUDE_PREAPPROVE`, record onboarding, Remote Control, trust, and MCP approval                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `coder-agent-start.sh`                                                               | Coder `coder_script`                 | the Coder agent's entry point: `docker-image-prune.sh`, `setup-gh-credential-helper.sh`, `opencode-web-start.sh` (each failure only warns), then exec `claude-remote-control-start.sh`                                                                                                                                                                                                                                                                                                                                                      |
| `docker-image-prune.sh`                                                              | Coder start, standalone `prepare`    | `docker image prune -af --filter until=72h`, printing the reclaimed total; exits 0 when docker or its daemon is unavailable, and only warns when the prune fails                                                                                                                                                                                                                                                                                                                                                                            |
| `claude-remote-control-start.sh`                                                     | Coder start, by hand                 | with a claude.ai login, run `claude-remote-control-session.sh` named after `CODER_WORKSPACE_NAME` in session `claude-remote` on `tmux -L claude-remote`                                                                                                                                                                                                                                                                                                                                                                                     |
| `opencode-web-start.sh`                                                              | Coder start, by hand                 | run the `coder-pane` command in session `opencode` on `tmux -L opencode` and print the `link`                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `opencode-web-command.sh link\|coder-hostname\|coder-pane\|coder-note\|serve\|probe` | the two OpenCode launchers, health   | print the server's root URL and build the Coder pane command, which runs `opencode serve` without `DISPLAY` on `0.0.0.0` with `OPENCODE_SERVER_PASSWORD` and otherwise on `127.0.0.1` with a password generated once into `~/.local/share/opencode/agentdev-server-password` (`0600`) and read by the pane, never on a command line; `coder-note` names that file; `serve` execs `opencode serve --port 4096 --hostname 0.0.0.0` in the workspace, refusing an empty password; `probe` needs a `version` from the authenticated `/api/info` |
| `claude-remote-control-session.sh`                                                   | `claude-remote` pane                 | resume the conversation pinned in `remote-control-session-id`; when none is stored or the resume fails, start and pin a new one                                                                                                                                                                                                                                                                                                                                                                                                             |
| `setup-gh-credential-helper.sh`                                                      | start, Coder start, standalone clone | `gh auth setup-git` when gh is logged in (an injected token counts) and no github.com helper exists; loads `${AGENTDEV_KEYRING_ENV_FILE}` first                                                                                                                                                                                                                                                                                                                                                                                             |
| `setup-keyring.sh`                                                                   | start                                | background dbus + gnome-keyring session over `runtime-keyring.sh`'s primitives, persisted to `${AGENTDEV_KEYRING_ENV_FILE:-.tmp/keyring-session.env}`                                                                                                                                                                                                                                                                                                                                                                                       |
| `firewall.sh`                                                                        | start                                | run `init-firewall.sh` only when `ENABLE_FIREWALL=true`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `setup-git-safe-directory.sh`, `setup-pre-commit.sh`                                 | start, standalone                    | add `safe.directory` once; hook install unless `AGENTDEV_SKIP_PRE_COMMIT`, strict and conflict-refusing in standalone mode                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `ci-hooks-repro.sh`                                                                  | by hand                              | run the hooks inside a bare `container:` job image to reproduce CI                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |

The standalone runtime, run by `agent-opencode`:

| Script                                                     | Run by                              | Does                                                                                                                                                                                                                                             |
| ---------------------------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `runtime-supervisor.py run\|control`                       | image `ENTRYPOINT`, supervisord     | `run`: exit `1` at once when Xpra is enabled and `XPRA_PASSWORD` is empty; otherwise bootstrap as root, then supervisord in-process, exit `1` after a terminal failure. `control`: the event listener that orders, probes, and recovers services |
| `runtime-bootstrap.sh`                                     | `run`, as root                      | create or reuse `agent` from `AGENTDEV_UID`/`AGENTDEV_GID`, `sudoers.d` entry, claim empty mount roots, lock-initialize or validate the shared auth volume, reset `XDG_RUNTIME_DIR`, then the firewall                                           |
| `runtime-firewall.sh`                                      | bootstrap                           | inert unless `ENABLE_FIREWALL=true`; validate the allowlist and `AGENTDEV_TRUSTED_PROXY_CIDRS`, run `init-firewall.sh`, admit the proxy to 4096/14500, filter nested egress in `DOCKER-USER`                                                     |
| `runtime-docker.sh run`                                    | `dockerd` program                   | refuse an unprivileged container, overlay storage, configured `hosts`, or a live second engine; exec one `dockerd` on `/var/run/docker.sock`                                                                                                     |
| `runtime-keyring.sh env\|dbus\|keyring\|check\|wait`       | `dbus`, `keyring` programs, sourced | foreground session bus on `$XDG_RUNTIME_DIR/bus` and gnome-keyring; readiness and non-destructive `login.keyring` primitives                                                                                                                     |
| `runtime-workspace.sh checkout\|project\|catalog\|prepare` | `prepare` program                   | reuse a valid checkout or clone into an empty one; uv and pre-commit for present configuration; register the checkout's or the image's catalog                                                                                                   |
| `runtime-cbm.sh install\|start\|check\|index\|run\|stop`   | `create`, `cbm`, `index` programs   | drive CBM through `daemon start/status/stop`, tracking PID plus start time; install from a user-owned copy of the pinned binary                                                                                                                  |
| `runtime-health.sh <service>\|ready`                       | controller, image `HEALTHCHECK`     | one probe per service, as the runtime user for user services; `ready` reads the aggregate marker                                                                                                                                                 |
| `test-agent-runtime.sh [pytest args]`                      | CI, by hand                         | container acceptance against `AGENTDEV_RUNTIME_TEST_IMAGE`, cleaning up labelled resources and failing an all-skipped run                                                                                                                        |

## How it works

Create installs the image-staged catalog for all three agents
(`AGENTDEV_CATALOG_DIR`, user scope for Claude); attach reinstalls from the
workspace with no argument, which defaults the root to this checkout and the
scope to `local`, so this repository develops the catalog in place while any
other project's attach finds no marketplace manifest and exits quietly. The
reinstall scripts list existing marketplaces whose path is the root, remove each
(uninstalling at every scope, tolerating "not found"), then add and install. The
Claude script reads every name from `.plugins[]` and loops; the Codex script
reads `.plugins[0]`, then runs that plugin's `bin/install-codex-agents.py` under
`python3 -B`, skipping a catalog that does not ship it. The OpenCode script
rewrites only the `plugin` array of
`${OPENCODE_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/opencode}/opencode.json`.
CBM wiring temporarily materializes the `~/.claude.json` symlink because the
installer rewrites the file, and first repairs Codex's `config.toml` so the
installer's hooks preflight accepts it.

`setup-agent-state.sh` is the one implementation of agent-state setup. Under
`AGENTDEV_RUNTIME_MODE=standalone` a real `~/.claude.json` is moved into the
Claude directory instead of discarded, CBM is installed through
`runtime-cbm.sh install` and is fatal, and the `gh-stack` extension the image
republishes under `/usr/local/lib/agentdev/gh-stack` is registered in the home.

Agent credentials come only from a login inside a container, kept in the shared
auth volume. `coder-agent-start.sh` is the single script the Coder workspace
template's `coder_script` runs: it prunes unused nested images, sets up the gh
helper with the agent's `GITHUB_TOKEN`, starts the OpenCode web UI, and execs
the Remote Control launcher. That launcher and `opencode-web-start.sh` each run
on a dedicated tmux server so the process inherits the caller's environment. The
OpenCode link is the server's root URL: `VSCODE_PROXY_URI` with `{{port}}` set
to 4096, or `http://127.0.0.1:4096`. OpenCode keeps its provider logins in its
own database in the per-instance data directory; no OpenCode credential is
shared.

Standalone, `runtime-workspace.sh prepare` runs the image prune, the checkout
step, `setup-agent-state.sh create` and `agent-policy`, the catalog, and the
project step once per container start. A checkout is reused when `git rev-parse`
resolves it and its common directory has objects; a clone writes a
`clone-in-progress` marker under `~/.local/state/agentdev` first and removes it
on success. The ordering, probes, and recovery the supervisor applies are in
[the standalone runtime
design](../../architecture/standalone-opencode-runtime.md).

## Depends on

The image's tools (`claude`, `codex`, `opencode`, `codebase-memory-mcp`, `uv`,
`jq`, `gnome-keyring-daemon`, `dockerd`, `xpra`, and, for the runtime,
supervisor) and the env variables the [runtime
contract](../api-image-runtime.md) lists. `uv-sync.sh` is also
`.devcontainer/scripts/uv-sync.sh` in the repository's own instructions.

## Invariants & gotchas

- `CBM_CACHE_DIR` unset is a hard failure in every CBM script; a missing binary
  is a soft skip. The devcontainer treats a failed CBM install as a warning;
  standalone stops. Bug:
  [cbm-codex-hooks-block-foreign-tables](../../bugs/cbm-codex-hooks-block-foreign-tables.md).
- `ENABLE_FIREWALL=true` with no `init-firewall.sh` in the image exits 1.
- A CI `container:` job supplies none of `devcontainer.json`'s env or mounts;
  `ci-hooks-repro.sh` exists because that difference is invisible from inside a
  devcontainer.
- `uv-sync.sh` removes only a `.venv` symlink pointing into `/uv/venvs/`, and
  never in standalone mode.
- The Remote Control launcher never passes `CLAUDE_CODE_OAUTH_TOKEN` to `claude`
  and exits 0 when the login is absent, expired, or not claude.ai.
- `opencode-web-start.sh` exits 0 when `opencode` or `tmux` is missing or the
  `opencode` session is live; a failed tmux start exits 1.
- `setup-gh-credential-helper.sh` loads the keyring session file, so in the
  devcontainer it runs after `setup-keyring.sh`. Standalone gets the session
  from the image's fixed `DBUS_SESSION_BUS_ADDRESS`.
- `configure-codex.py` rewrites `config.toml` through `tomlkit`, keeping other
  tools' comments. Decision:
  [codex-full-access-in-devcontainer](../../architecture/codex-full-access-in-devcontainer.md).
- `configure-opencode.py` parses JSON and JSONC through pinned `json5`,
  preserves setting values, and normalizes the selected file to strict JSON.
  Decision:
  [opencode-full-access-in-devcontainer](../../architecture/opencode-full-access-in-devcontainer.md).
- The CBM daemon is per account and rendezvous directory, never per cache: [CBM
  daemon lifecycle](../../architecture/cbm-daemon-lifecycle.md).
- `runtime-health.sh` names match the supervisord program names, which the
  controller passes verbatim.

## Key references

Verified anchor points (line numbers as of 2026-10-20):

- `.devcontainer/scripts/postCreateCommand.sh:56` —
  `setup-agent-state.sh create`; `:70` — staged-catalog install
- `.devcontainer/scripts/postStartCommand.sh:9-30` — the start sequence
- `.devcontainer/scripts/postAttachCommand.sh:14-16` — workspace reinstall
- `.devcontainer/scripts/setup-agent-state.sh:14` — `link_claude_json`; `:31` —
  `install_cbm`; `:51` — `register_user_tools`; `:69` — `cmd_create`
- `.devcontainer/scripts/link-codex-auth.sh:23-25` — overridable auth roots
- `.devcontainer/scripts/reinstall-agentdev-claude.sh:74-76` — add + install
- `.devcontainer/scripts/reinstall-agentdev-codex.sh:64-65` — add + install;
  `:69-76` — Codex agent install
- `.devcontainer/scripts/reinstall-agentdev-opencode.sh:32-38` — bridge entry
  rewrite
- `.devcontainer/scripts/codebase-memory-mcp-install.sh:55-75` — symlink
  materialization and restore; `:79` — hooks-block repair
- `.devcontainer/scripts/uv-sync.sh:24` — managed-link removal outside
  standalone
- `.devcontainer/scripts/setup-pre-commit.sh:19` — strict standalone hook setup
- `.devcontainer/scripts/setup-git-safe-directory.sh:12` — add once
- `.devcontainer/scripts/opencode-web-start.sh:15-17,24` — link, hostname,
  password note, and pane from `opencode-web-command.sh`
- `.devcontainer/scripts/opencode-web-command.sh:19` — `link`; `:38` —
  `coder_pane`; `:62` — `probe`; `:76` — `serve`
- `.devcontainer/scripts/setup-gh-credential-helper.sh:8` — keyring session file
- `.devcontainer/scripts/setup-keyring.sh:32` — session file location
- `.devcontainer/scripts/runtime-supervisor.py:352` — `run`; `:358-364` — the
  `XPRA_PASSWORD` refusal
- `.devcontainer/scripts/runtime-bootstrap.sh:93` — `claim_instance_dir`; `:123`
  — `prepare_shared_auth`; `:169` — firewall last
- `.devcontainer/scripts/runtime-workspace.sh:26` — `validate_checkout`; `:40` —
  `clone_workspace`; `:87` — `select_catalog`; `:107` — `cmd_prepare`
- `.devcontainer/scripts/runtime-cbm.sh:81` — `kill_generation`; `:93` —
  `cmd_install`; `:178` — `cmd_run`
- `.devcontainer/scripts/runtime-keyring.sh:79,86` — foreground bus and keyring
- `.devcontainer/scripts/runtime-docker.sh:61` — the `dockerd` exec
- `.devcontainer/scripts/runtime-firewall.sh:48` — proxy ingress; `:57` — nested
  egress
- `.devcontainer/scripts/setup-agent-state.sh:60` — `apply_agent_policy`
- `.devcontainer/scripts/configure-codex.py:29,46` — `render_config`,
  `write_atomically`
- `.devcontainer/scripts/configure-opencode.py:19,30,36,49,75,89` — config
  resolution, parsing, policy merge, atomic write, and entry point
