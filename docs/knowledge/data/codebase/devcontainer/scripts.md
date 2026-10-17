---
type: codebase
description: 'The postCreate, postStart, and postAttach hooks and the helpers they call: catalog reinstalls, codebase-memory-mcp wiring, uv sync, keyring, firewall gate, Codex and OpenCode auth symlinks, Claude pre-approval, gh credential helper, the Coder agent-start entry point, Claude Remote Control, the OpenCode web UI, Codex policy.'
source: .devcontainer/scripts
source_digest: sha256:652c8ac31492a03878558faf4908a66efb6d898c65f11744c5d1819e9e60c0d8
verified:
  by: claude-code/opus-5.5
  at: 2026-10-17T05:20:00Z
stale_after: 2027-01-15
generated:
  by: claude-code/opus-5.5
  at: 2026-10-17T05:20:00Z
sources:
- id: code
  resource: .devcontainer/scripts
---

# Devcontainer lifecycle scripts

Twenty-four shell scripts, all `set -euo pipefail`, and two `uv run --script`
Python scripts that the three lifecycle commands in
[devcontainer.json](../devcontainer.md) fan out to. Each resolves the workspace
from `DEV_WORKSPACE_FOLDER` with a `BASH_SOURCE` fallback so it also runs
outside the devcontainer.

## Public surface

| Script                                               | Called by                       | Does                                                                                                                                                                                                                             |
| ---------------------------------------------------- | ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `postCreateCommand.sh`                               | create (once)                   | ownership fixes, `~/.claude.json` symlink, CBM install, auth dirs, Claude pre-approval, Codex and OpenCode auth links, uv sync, staged-catalog install                                                                           |
| `postStartCommand.sh`                                | every start                     | CBM daemon + index, git safe.directory, pre-commit hooks, keyring, gh helper, firewall gate, Xpra, Codex and OpenCode auth links, Codex policy                                                                                   |
| `postAttachCommand.sh`                               | every editor attach             | CBM index, uv sync, reinstall the catalog from this checkout                                                                                                                                                                     |
| `reinstall-agentdev-claude.sh [root] [scope]`        | create, attach                  | remove stale marketplaces for `root`, add it, install every published plugin at `scope`                                                                                                                                          |
| `reinstall-agentdev-codex.sh [root]`                 | create, attach                  | the Codex equivalent, single-plugin; Codex has no scopes                                                                                                                                                                         |
| `reinstall-agentdev-opencode.sh [root]`              | create, attach                  | point the `plugin` list of the user's `opencode.json` at `root`'s OpenCode bridge, replacing any earlier bridge entry                                                                                                            |
| `codebase-memory-mcp-{install,start,index}.sh`       | create, start, attach           | agent-config wiring, daemon start, repository index                                                                                                                                                                              |
| `repair-codex-cbm-hooks-block.py`                    | CBM install                     | move tables other than cbm's own hooks out of its `SessionStart` block in `${CODEX_HOME:-~/.codex}/config.toml`; no-op when nothing needs moving                                                                                 |
| `uv-sync.sh`                                         | create, attach                  | drop a managed `.venv` link, `uv sync --all-groups --all-extras` into `/uv`                                                                                                                                                      |
| `link-codex-auth.sh`                                 | create, start                   | symlink `~/.codex/auth.json` into the shared auth volume                                                                                                                                                                         |
| `link-opencode-auth.sh`                              | create, start                   | move a regular `${XDG_DATA_HOME:-~/.local/share}/opencode/auth.json` into `${AGENTDEV_AGENTS_AUTH_DIR:-/root/.agents-auth}/opencode/` and symlink it back, without creating the target                                           |
| `configure-codex.py`                                 | start (last)                    | set top-level `sandbox_mode` and `approval_policy` in `${CODEX_HOME:-~/.codex}/config.toml`, atomically at `0600`                                                                                                                |
| `preapprove-claude-workspace.sh`                     | create                          | unless `AGENTDEV_SKIP_CLAUDE_PREAPPROVE`, record onboarding, Remote Control, trust, and MCP approval                                                                                                                             |
| `coder-agent-start.sh`                               | Coder `coder_script`            | the Coder agent's entry point: run `docker-image-prune.sh`, then `setup-gh-credential-helper.sh`, then `opencode-web-start.sh` (each failure only warns), then exec `claude-remote-control-start.sh`                             |
| `docker-image-prune.sh`                              | `coder-agent-start.sh`          | `docker image prune -af --filter until=72h` on the nested engine, printing the reclaimed total; exits 0 when docker or its daemon is unavailable, and only warns when the prune fails                                            |
| `claude-remote-control-start.sh`                     | `coder-agent-start.sh`, by hand | with a claude.ai login, run `claude-remote-control-session.sh` named after `CODER_WORKSPACE_NAME` in session `claude-remote` on `tmux -L claude-remote`                                                                          |
| `opencode-web-start.sh`                              | `coder-agent-start.sh`, by hand | run `opencode web --port 4096` without `DISPLAY` in session `opencode` on `tmux -L opencode`, bound to `0.0.0.0` when `OPENCODE_SERVER_PASSWORD` is non-empty and `127.0.0.1` otherwise; prints a link into the workspace folder |
| `claude-remote-control-session.sh`                   | `claude-remote` pane            | resume the conversation pinned in `remote-control-session-id`; when none is stored or the resume fails, start and pin a new one                                                                                                  |
| `setup-gh-credential-helper.sh`                      | start, `coder-agent-start.sh`   | `gh auth setup-git` when gh is logged in and no github.com helper exists                                                                                                                                                         |
| `setup-keyring.sh`                                   | start                           | dbus + gnome-keyring session, persisted to `.tmp/keyring-session.env`                                                                                                                                                            |
| `firewall.sh`                                        | start                           | run `init-firewall.sh` only when `ENABLE_FIREWALL=true`                                                                                                                                                                          |
| `setup-git-safe-directory.sh`, `setup-pre-commit.sh` | start                           | `safe.directory`; hook install unless `AGENTDEV_SKIP_PRE_COMMIT`                                                                                                                                                                 |
| `ci-hooks-repro.sh`                                  | by hand                         | run the hooks inside a bare `container:` job image to reproduce CI                                                                                                                                                               |

## How it works

Create installs the image-staged catalog for all three agents
(`AGENTDEV_CATALOG_DIR`, user scope for Claude); attach reinstalls from the
workspace with no argument, which defaults the root to this checkout and the
scope to `local`, so this repository develops the catalog in place while any
other project's attach finds no marketplace manifest and exits quietly. The
reinstall scripts list existing marketplaces whose path is the root, remove each
(uninstalling at every scope, tolerating "not found"), then add and install. The
Claude script reads every name from `.plugins[]` and loops, so the Claude
marketplace's two plugins both install; the Codex script reads `.plugins[0]`,
which is accurate because its manifest publishes one, then runs that plugin's
`bin/install-codex-agents.py` under `python3 -B`, skipping a catalog that does
not ship it. The OpenCode script rewrites only the `plugin` array of
`${OPENCODE_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/opencode}/opencode.json`,
creating the file when absent, and exits quietly when `root` ships no
`.opencode-plugin/`. CBM wiring temporarily materializes the `~/.claude.json`
symlink because the installer rewrites the file, and first repairs Codex's
`config.toml` so the installer's hooks preflight accepts it.

Agent credentials come only from a login inside a container, kept in the shared
auth volume. `claude-remote-control-start.sh` asks `claude auth status --json`
and starts Remote Control only when it reports `loggedIn` with the `claude.ai`
auth method. No lifecycle hook runs it. `coder-agent-start.sh` is the single
script the Coder workspace template's `coder_script` on the dev container's
sub-agent runs, outside this repository; it prunes unused images in the nested
Docker engine, then sets up the gh credential helper with the agent's
environment, where `GITHUB_TOKEN` is set, then starts the OpenCode web UI, then
execs the Remote Control launcher. That launcher runs the session on its own
tmux server, so the Claude process inherits the caller's environment even when a
default-socket server is already live. The pane runs
`claude-remote-control-session.sh`, which keeps one conversation ID in
`${CLAUDE_CONFIG_DIR:-~/.claude}/remote-control-session-id` and passes it to
`claude --remote-control --resume`; a missing ID or a non-zero resume exit
starts `--session-id` with a fresh UUID written to that file.
`opencode-web-start.sh` uses the same dedicated-server pattern with no login
gate, so `OPENCODE_SERVER_PASSWORD` from the agent's environment reaches the
server. On a start or a reuse it prints `<base>/<base64url(workspace)>/session`,
where `<base>` is `VSCODE_PROXY_URI` with `{{port}}` set to 4096, or
`http://127.0.0.1:4096` when that variable is unset.

## Depends on

The image's tools (`claude`, `codex`, `codebase-memory-mcp`, `uv`, `jq`,
`gnome-keyring-daemon`) and the env variables the [runtime
contract](../api-image-runtime.md) lists. `uv-sync.sh` is also
`.devcontainer/scripts/uv-sync.sh` in the repository's own instructions.

## Invariants & gotchas

- `CBM_CACHE_DIR` unset is a hard failure in every CBM script; a missing binary
  is a soft skip. postCreate treats a failed CBM install as a warning and
  continues. Bug:
  [cbm-codex-hooks-block-foreign-tables](../../bugs/cbm-codex-hooks-block-foreign-tables.md).
- `ENABLE_FIREWALL=true` with no `init-firewall.sh` in the image exits 1.
- A CI `container:` job supplies none of `devcontainer.json`'s env or mounts;
  `ci-hooks-repro.sh` exists because that difference is invisible from inside a
  devcontainer.
- `uv-sync.sh` removes only a `.venv` symlink pointing into `/uv/venvs/`; a
  foreign `.venv` is left alone with a warning.
- The Remote Control launcher never passes `CLAUDE_CODE_OAUTH_TOKEN` to
  `claude`, including to the status check, and exits 0 when the login is absent,
  expired, or not claude.ai.
- `opencode-web-start.sh` exits 0 when `opencode` or `tmux` is missing or the
  `opencode` session is live; a failed tmux start exits 1.
- `setup-gh-credential-helper.sh` sources `.tmp/keyring-session.env`, so it must
  run after `setup-keyring.sh`.
- `configure-codex.py` rewrites `config.toml` through `tomlkit`, keeping other
  tools' comments; keys it adds go above everything else in the file. Decision:
  [codex-full-access-in-devcontainer](../../architecture/codex-full-access-in-devcontainer.md).

## Key references

Verified anchor points (line numbers as of 2026-10-17):

- `.devcontainer/scripts/postCreateCommand.sh:56-62` — `~/.claude.json` symlink
  into the volume
- `.devcontainer/scripts/postCreateCommand.sh:67-68` — non-fatal CBM install
- `.devcontainer/scripts/postCreateCommand.sh:74` — Claude pre-approval
- `.devcontainer/scripts/postCreateCommand.sh:79-80` — Codex and OpenCode auth
  links
- `.devcontainer/scripts/postCreateCommand.sh:93-99` — staged-catalog install
- `.devcontainer/scripts/postStartCommand.sh:9-31` — the start sequence
- `.devcontainer/scripts/postAttachCommand.sh:14-16` — workspace reinstall
- `.devcontainer/scripts/reinstall-agentdev-claude.sh:74-76` — add + install
- `.devcontainer/scripts/reinstall-agentdev-codex.sh:64-65` — add + install
- `.devcontainer/scripts/reinstall-agentdev-codex.sh:69-76` — Codex agent
  install, skipped for a catalog without the installer
- `.devcontainer/scripts/reinstall-agentdev-opencode.sh:32-38` — bridge entry
  rewrite
- `.devcontainer/scripts/codebase-memory-mcp-install.sh:55-75` — symlink
  materialization and restore
- `.devcontainer/scripts/codebase-memory-mcp-install.sh:79` — hooks-block repair
  ahead of the installer
- `.devcontainer/scripts/repair-codex-cbm-hooks-block.py:47` — `repair`
- `.devcontainer/scripts/uv-sync.sh:23-32` — managed-link removal and sync
- `.devcontainer/scripts/preapprove-claude-workspace.sh:6` — opt-out gate
- `.devcontainer/scripts/claude-remote-control-start.sh:12-27,31-35,42-44` —
  login gate, workspace-named session, token-free launch of the pane script on
  `tmux -L claude-remote`
- `.devcontainer/scripts/claude-remote-control-session.sh:5,15,19-22` — ID file,
  resume, fresh pinned conversation
- `.devcontainer/scripts/coder-agent-start.sh:9-21` — warn-only image prune,
  helper setup, and OpenCode start, exec of the Remote Control launcher
- `.devcontainer/scripts/opencode-web-start.sh:17-21` — workspace link from
  `VSCODE_PROXY_URI`; `:24-27,29,35-36` — password-gated bind, live-session
  reuse, `DISPLAY`-free launch on `tmux -L opencode`
- `.devcontainer/scripts/link-opencode-auth.sh:13,16,21` — private shared
  directory, move of a regular file, symlink
- `.devcontainer/scripts/docker-image-prune.sh:7-21` — docker and daemon gates,
  warn-only prune
- `.devcontainer/scripts/setup-gh-credential-helper.sh:8,30` — keyring session
  load, `gh auth setup-git`
- `.devcontainer/scripts/configure-codex.py:29,46` — `render_config`,
  `write_atomically`
