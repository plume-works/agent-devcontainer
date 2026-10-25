---
type: codebase
description: The postCreate, postStart, and postAttach hooks and the helpers they call — agent-state setup, catalog reinstalls, codebase-memory-mcp wiring, uv sync, keyring, firewall gate, auth links and full-access policies, gh credential helper, the Coder agent-start entry point, Remote Control, the OpenCode web UI — plus the standalone agent-opencode runtime built from the same helpers.
source: .devcontainer/scripts
source_digest: sha256:f4ab319edd902f5bbeb013233426cae29d8d72ebc8a02f4592d086e3f02bfafd
verified:
  by: claude-code/opus-5.5
  at: 2026-10-24T04:17:27Z
stale_after: 2027-01-23
generated:
  by: claude-code/opus-5.5
  at: 2026-10-24T04:17:27Z
sources:
- id: code
  resource: .devcontainer/scripts
---

# Devcontainer lifecycle scripts

Thirty-six shell scripts, all `set -euo pipefail` except the sourced
`runtime-paths.sh`, and four Python scripts. The three lifecycle commands in
[devcontainer.json](../devcontainer.md) fan out to them. The `agent-opencode`
image bakes the whole directory into `/opt/agentdev-runtime` and runs the
`runtime-*` scripts as its standalone lifecycle. Most scripts resolve the
workspace from `DEV_WORKSPACE_FOLDER`, with a `BASH_SOURCE` fallback.

## Public surface

Devcontainer lifecycle and shared helpers:

| Script                                                                               | Called by                                     | Does                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------------------------------------------------------------------------------ | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `postCreateCommand.sh`                                                               | create (once)                                 | ownership fixes, `setup-agent-state.sh create`, uv sync, `setup-agent-state.sh catalog <staged> user`                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `postStartCommand.sh`                                                                | every start                                   | CBM daemon + index, git safe.directory, pre-commit hooks, keyring, gh helper, firewall gate, Xpra, `setup-agent-state.sh links`, then `agent-policy`                                                                                                                                                                                                                                                                                                                                                                                        |
| `postAttachCommand.sh`                                                               | every editor attach                           | background CBM index request, uv sync, `setup-agent-state.sh catalog` for this checkout                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `setup-agent-state.sh create\|links\|agent-policy\|cbm\|catalog <dir> [scope]`       | both hooks, standalone `prepare` and `config` | `create`: register image user tooling (standalone), link `~/.claude.json` into the Claude dir, CBM install (devcontainer only), auth dirs `0700`, Claude pre-approval, Codex auth link. `agent-policy`: both `configure-*.py`. `cbm`: the CBM install. `catalog`: the three reinstall scripts, scope to Claude only. All but `links` hold `~/.local/state/agentdev/agent-config.lock`                                                                                                                                                       |
| `runtime-paths.sh`                                                                   | sourced                                       | the auth, Claude, Codex, and OpenCode roots, each `/root`-layout by default and overridable; `agentdev_standalone` reads `AGENTDEV_RUNTIME_MODE`                                                                                                                                                                                                                                                                                                                                                                                            |
| `reinstall-agentdev-claude.sh [root] [scope]`                                        | `catalog`, attach                             | remove stale marketplaces for `root`, add it, install every published plugin at `scope`                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `reinstall-agentdev-codex.sh [root]`                                                 | `catalog`, attach                             | the Codex equivalent, single-plugin; Codex has no scopes. Leaves a registration whose name, root, version, and plugin cache already match in place                                                                                                                                                                                                                                                                                                                                                                                          |
| `reinstall-agentdev-opencode.sh [root]`                                              | `catalog`, attach                             | point the `plugin` list of the user's `opencode.json` at `root`'s OpenCode bridge, replacing any earlier bridge entry                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `codebase-memory-mcp-{install,start,index}.sh`                                       | `create`, `cbm`, start, attach                | agent-config wiring with an empty `hooks.json` seeded first, daemon start, an async index request that returns once CBM accepts it                                                                                                                                                                                                                                                                                                                                                                                                          |
| `repair-codex-cbm-hooks-block.py`                                                    | CBM install                                   | move tables other than cbm's own hooks out of its `SessionStart` block in `${CODEX_HOME:-~/.codex}/config.toml`; remove an orphaned marker and the canonical tables of its block, keeping comments and the user's other hooks and refusing a foreign one; LF/CRLF and mode kept                                                                                                                                                                                                                                                             |
| `uv-sync.sh`                                                                         | create, attach, standalone                    | drop a managed `.venv` link (not in standalone mode), `uv sync --all-groups --all-extras` into `/uv`                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `link-codex-auth.sh`                                                                 | `create`, `links`                             | move a regular credential file into its subdirectory of the shared auth root and symlink it back                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `configure-codex.py`                                                                 | `agent-policy`                                | set top-level `sandbox_mode` and `approval_policy` in `${CODEX_HOME:-~/.codex}/config.toml`, atomically at `0600`                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `configure-opencode.py`                                                              | `agent-policy`                                | merge the approved action and external-filesystem policy into the highest-precedence JSON or JSONC user config, atomically at `0600`                                                                                                                                                                                                                                                                                                                                                                                                        |
| `preapprove-claude-workspace.sh`                                                     | `create`                                      | unless `AGENTDEV_SKIP_CLAUDE_PREAPPROVE`, record onboarding, Remote Control, trust, and MCP approval                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `coder-agent-start.sh`                                                               | Coder `coder_script`                          | the Coder agent's entry point: `docker-image-prune.sh`, `setup-gh-credential-helper.sh`, `opencode-web-start.sh` (each failure only warns), then exec `claude-remote-control-start.sh`                                                                                                                                                                                                                                                                                                                                                      |
| `docker-image-prune.sh`                                                              | Coder start, standalone `prepare`             | `docker image prune -af --filter until=72h`, printing the reclaimed total; exits 0 when docker or its daemon is unavailable, and only warns when the prune fails                                                                                                                                                                                                                                                                                                                                                                            |
| `claude-remote-control-start.sh`                                                     | Coder start, by hand                          | with a claude.ai login, run `claude-remote-control-session.sh` named after `CODER_WORKSPACE_NAME`, or with `AGENTDEV_CLAUDE_RC_MODE=server` `claude remote-control --spawn same-dir`, in session `claude-remote` on `tmux -L claude-remote`                                                                                                                                                                                                                                                                                                 |
| `opencode-web-start.sh`                                                              | Coder start, by hand                          | run the `coder-pane` command in session `opencode` on `tmux -L opencode` and print the `link`                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `opencode-web-command.sh link\|coder-hostname\|coder-pane\|coder-note\|serve\|probe` | the two OpenCode launchers, health            | print the server's root URL and build the Coder pane command, which runs `opencode serve` without `DISPLAY` on `0.0.0.0` with `OPENCODE_SERVER_PASSWORD` and otherwise on `127.0.0.1` with a password generated once into `~/.local/share/opencode/agentdev-server-password` (`0600`) and read by the pane, never on a command line; `coder-note` names that file; `serve` execs `opencode serve --port 4096 --hostname 0.0.0.0` in the workspace, refusing an empty password; `probe` needs a `version` from the authenticated `/api/info` |
| `claude-remote-control-session.sh`                                                   | `claude-remote` pane                          | resume the conversation pinned in `remote-control-session-id`; when none is stored or the resume fails, start and pin a new one; both calls get a `--settings` `SessionStart` hook running `claude-remote-control-pin.sh`                                                                                                                                                                                                                                                                                                                   |
| `claude-remote-control-pin.sh`                                                       | `claude-remote` `SessionStart` hook           | write the hook input's `session_id` to `remote-control-session-id` atomically, so the pin follows `/clear`; leave it unchanged on unusable input and always exit 0                                                                                                                                                                                                                                                                                                                                                                          |
| `setup-gh-credential-helper.sh`                                                      | start, Coder start, standalone clone          | `gh auth setup-git` when gh is logged in (an injected token counts) and no github.com helper exists; loads `${AGENTDEV_KEYRING_ENV_FILE}` first                                                                                                                                                                                                                                                                                                                                                                                             |
| `setup-keyring.sh`                                                                   | start                                         | dbus + gnome-keyring session over `runtime-keyring.sh`'s primitives, at containerEnv's fixed `DBUS_SESSION_BUS_ADDRESS` when set, persisted to `${AGENTDEV_KEYRING_ENV_FILE:-.tmp/keyring-session.env}`                                                                                                                                                                                                                                                                                                                                     |
| `firewall.sh`                                                                        | start                                         | run `init-firewall.sh` only when `ENABLE_FIREWALL=true`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `environment-health.sh`                                                              | by hand                                       | read-only PASS/FAIL/SKIP report of tools, services, auth links, and network for the devcontainer or standalone mode; exits `1` on any FAIL and never prints auth output                                                                                                                                                                                                                                                                                                                                                                     |
| `setup-git-safe-directory.sh`, `setup-pre-commit.sh`                                 | start, standalone                             | add `safe.directory` once; hook install unless `AGENTDEV_SKIP_PRE_COMMIT`; standalone registers hook scripts without building environments and refuses conflicts                                                                                                                                                                                                                                                                                                                                                                            |
| `ci-hooks-repro.sh`                                                                  | by hand                                       | run the hooks inside a bare `container:` job image to reproduce CI                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |

The standalone runtime, run by `agent-opencode`:

| Script                                                             | Run by                                  | Does                                                                                                                                                                                                                                                                                                                                                                                |
| ------------------------------------------------------------------ | --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `runtime-supervisor.py run\|control\|exec\|retry`                  | image `ENTRYPOINT`, supervisord         | `run`: check settings and `XPRA_PASSWORD`, bootstrap as root, then supervisord in-process; a failure before supervisord latches PID 1 until `retry`; exit `1` only when the controller dies. `control`: the event listener that orders, probes, recovers, degrades, and latches. `exec`: run one program, keeping a live tail of its output. `retry [component]`: rerun what failed |
| `runtime-bootstrap.sh`                                             | `run`, as root                          | create or reuse `agent` from `AGENTDEV_UID`/`AGENTDEV_GID`, `sudoers.d` entry, claim empty mount roots, lock-initialize or validate the shared auth volume, reset `XDG_RUNTIME_DIR`, then the firewall                                                                                                                                                                              |
| `runtime-firewall.sh`                                              | bootstrap                               | inert unless `ENABLE_FIREWALL=true`; validate the allowlist and `AGENTDEV_TRUSTED_PROXY_CIDRS`, run `init-firewall.sh`, admit the proxy to 4096/14500, filter nested egress in `DOCKER-USER`                                                                                                                                                                                        |
| `runtime-docker.sh run`                                            | `dockerd` program                       | refuse an unprivileged container, overlay storage, configured `hosts`, or a live second engine; exec one `dockerd` on `/var/run/docker.sock`                                                                                                                                                                                                                                        |
| `runtime-keyring.sh env\|dbus\|keyring\|check\|wait`               | `dbus`, `keyring` programs, sourced     | foreground session bus on `$XDG_RUNTIME_DIR/bus` and gnome-keyring; readiness and non-destructive `login.keyring` primitives                                                                                                                                                                                                                                                        |
| `runtime-workspace.sh checkout\|project\|catalog\|config\|prepare` | `prepare`, `config`, `project` programs | `prepare`: reuse or clone the checkout, agent state, agent policy. `config`: register the checkout's or the image's catalog, then install CBM. `project`: uv and pre-commit for present configuration                                                                                                                                                                               |
| `runtime-cbm.sh install\|start\|check\|index\|run\|stop`           | `create`, `cbm`, `index` programs       | drive CBM through `daemon start/status/stop`, tracking PID plus start time; install from a user-owned copy of the pinned binary                                                                                                                                                                                                                                                     |
| `runtime-health.sh <service>\|ready\|status`                       | controller, image `HEALTHCHECK`         | one probe per service, as the runtime user for user services; `ready`: a heartbeat under three intervals old, state `ready`, and live core probes; `status`: state, failures, retry commands, last failure record                                                                                                                                                                   |
| `test-agent-runtime.sh [pytest args]`                              | CI, by hand                             | container acceptance against `AGENTDEV_RUNTIME_TEST_IMAGE`, cleaning up labelled resources and failing an all-skipped run                                                                                                                                                                                                                                                           |

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
Claude directory instead of discarded, CBM is installed by the separate `cbm`
step through `runtime-cbm.sh install` and fails it, and the `gh-stack` extension
the image republishes under `/usr/local/lib/agentdev/gh-stack` is registered in
the home.

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

Standalone, the supervisor runs `runtime-workspace.sh prepare` (checkout,
`setup-agent-state.sh create`, `agent-policy`), `config`, and `project` as
separate one-shots once per container start. A checkout is reused when
`git rev-parse` resolves it and its common directory has objects; a clone writes
a `clone-in-progress` marker under `~/.local/state/agentdev` first and removes
it on success. The ordering, probes, and recovery the supervisor applies are in
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
  standalone fails the optional `config` step. Bug:
  [cbm-codex-hooks-block-foreign-tables](../../bugs/cbm-codex-hooks-block-foreign-tables.md).
- `ENABLE_FIREWALL=true` with no `init-firewall.sh` in the image exits 1.
- A CI `container:` job supplies none of `devcontainer.json`'s env or mounts;
  `ci-hooks-repro.sh` exists because that difference is invisible from inside a
  devcontainer.
- `uv-sync.sh` removes only a `.venv` symlink pointing into `/uv/venvs/`, and
  never in standalone mode.
- The Remote Control launcher never passes `CLAUDE_CODE_OAUTH_TOKEN` to `claude`
  and exits 0 when the login is absent, expired, or not claude.ai. An
  `AGENTDEV_CLAUDE_RC_MODE` other than `server` or `session` exits 1 first.
  Decision: [Claude Remote Control server
  mode](../../architecture/claude-remote-control-server-mode.md).
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

Verified anchor points (line numbers as of 2026-10-23):

- `.devcontainer/scripts/postCreateCommand.sh:56` —
  `setup-agent-state.sh create`; `:70` — staged-catalog install
- `.devcontainer/scripts/postStartCommand.sh:9-30` — the start sequence
- `.devcontainer/scripts/postAttachCommand.sh:14` — workspace catalog through
  `setup-agent-state.sh`
- `.devcontainer/scripts/setup-agent-state.sh:15` — `link_claude_json`; `:32` —
  `install_cbm`; `:52` — `register_user_tools`; `:70` — `cmd_create`; `:83` —
  `with_config_lock`
- `.devcontainer/scripts/link-codex-auth.sh:23-25` — overridable auth roots
- `.devcontainer/scripts/reinstall-agentdev-claude.sh:74-76` — add + install
- `.devcontainer/scripts/reinstall-agentdev-codex.sh:63` — `registered`;
  `:83-84` — add + install; `:89` — Codex agent install
- `.devcontainer/scripts/reinstall-agentdev-opencode.sh:32-38` — bridge entry
  rewrite
- `.devcontainer/scripts/codebase-memory-mcp-install.sh:55-75` — symlink
  materialization and restore; `:81` — `hooks.json` seed; `:85` — hooks-block
  repair
- `.devcontainer/scripts/uv-sync.sh:24` — managed-link removal outside
  standalone
- `.devcontainer/scripts/setup-pre-commit.sh:33` — standalone hook registration
- `.devcontainer/scripts/setup-git-safe-directory.sh:12` — add once
- `.devcontainer/scripts/opencode-web-start.sh:15-17,24` — link, hostname,
  password note, and pane from `opencode-web-command.sh`
- `.devcontainer/scripts/opencode-web-command.sh:19` — `link`; `:38` —
  `coder_pane`; `:62` — `probe`; `:76` — `serve`
- `.devcontainer/scripts/setup-gh-credential-helper.sh:8` — keyring session file
- `.devcontainer/scripts/setup-keyring.sh:32` — session file location
- `.devcontainer/scripts/runtime-supervisor.py:855` — `run`; `:805` —
  `preflight`; `:925` — `exec`; `:955` — `retry`
- `.devcontainer/scripts/runtime-bootstrap.sh:93` — `claim_instance_dir`; `:123`
  — `prepare_shared_auth`; `:169` — firewall last
- `.devcontainer/scripts/runtime-workspace.sh:27` — `validate_checkout`; `:41` —
  `clone_workspace`; `:88` — `select_catalog`; `:108` — `cmd_prepare`; `:116` —
  `cmd_config`
- `.devcontainer/scripts/runtime-cbm.sh:80` — `kill_generation`; `:92` —
  `cmd_install`; `:154` — `cmd_index`; `:179` — `cmd_run`
- `.devcontainer/scripts/runtime-keyring.sh:79,86` — foreground bus and keyring
- `.devcontainer/scripts/runtime-docker.sh:61` — the `dockerd` exec
- `.devcontainer/scripts/runtime-firewall.sh:48` — proxy ingress; `:57` — nested
  egress
- `.devcontainer/scripts/setup-agent-state.sh:61` — `apply_agent_policy`
- `.devcontainer/scripts/codebase-memory-mcp-index.sh:20` — the async request
- `.devcontainer/scripts/configure-codex.py:29,46` — `render_config`,
  `write_atomically`
- `.devcontainer/scripts/configure-opencode.py:19,30,36,49,75,89` — config
  resolution, parsing, policy merge, atomic write, and entry point
