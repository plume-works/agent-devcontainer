---
type: codebase
description: 'The postCreate, postStart, and postAttach hooks and the helpers they call: catalog reinstalls, codebase-memory-mcp wiring, uv sync, keyring, firewall gate, Codex auth symlink, Claude pre-approval, gh credential helper, the Coder agent-start entry point, Claude Remote Control, Codex policy.'
source: .devcontainer/scripts
source_digest: sha256:debc9cf94736e1efb5c480ae30883de12ce73a4d935eeb3b6e58a83d19d47640
verified:
  by: claude-code/opus-5.5
  at: 2026-10-11T19:11:56Z
stale_after: 2027-01-09
generated:
  by: claude-code/opus-5.5
  at: 2026-10-11T19:11:56Z
sources:
- id: code
  resource: .devcontainer/scripts
---

# Devcontainer lifecycle scripts

Twenty shell scripts, all `set -euo pipefail`, and two `uv run --script` Python
scripts that the three lifecycle commands in
[devcontainer.json](../devcontainer.md) fan out to. Each resolves the workspace
from `DEV_WORKSPACE_FOLDER` with a `BASH_SOURCE` fallback so it also runs
outside the devcontainer.

## Public surface

| Script                                               | Called by                       | Does                                                                                                                                             |
| ---------------------------------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `postCreateCommand.sh`                               | create (once)                   | ownership fixes, `~/.claude.json` symlink, CBM install, auth dirs, Claude pre-approval, Codex auth link, uv sync, staged-catalog install         |
| `postStartCommand.sh`                                | every start                     | CBM daemon + index, git safe.directory, pre-commit hooks, keyring, gh helper, firewall gate, Xpra, Codex auth link and policy                    |
| `postAttachCommand.sh`                               | every editor attach             | CBM index, uv sync, reinstall the catalog from this checkout                                                                                     |
| `reinstall-agentdev-claude.sh [root] [scope]`        | create, attach                  | remove stale marketplaces for `root`, add it, install every published plugin at `scope`                                                          |
| `reinstall-agentdev-codex.sh [root]`                 | create, attach                  | the Codex equivalent, single-plugin; Codex has no scopes                                                                                         |
| `reinstall-agentdev-opencode.sh [root]`              | create, attach                  | point the `plugin` list of the user's `opencode.json` at `root`'s OpenCode bridge, replacing any earlier bridge entry                            |
| `codebase-memory-mcp-{install,start,index}.sh`       | create, start, attach           | agent-config wiring, daemon start, repository index                                                                                              |
| `repair-codex-cbm-hooks-block.py`                    | CBM install                     | move tables other than cbm's own hooks out of its `SessionStart` block in `${CODEX_HOME:-~/.codex}/config.toml`; no-op when nothing needs moving |
| `uv-sync.sh`                                         | create, attach                  | drop a managed `.venv` link, `uv sync --all-groups --all-extras` into `/uv`                                                                      |
| `link-codex-auth.sh`                                 | create, start                   | symlink `~/.codex/auth.json` into the shared auth volume                                                                                         |
| `configure-codex.py`                                 | start (last)                    | set top-level `sandbox_mode` and `approval_policy` in `${CODEX_HOME:-~/.codex}/config.toml`, atomically at `0600`                                |
| `preapprove-claude-workspace.sh`                     | create                          | unless `AGENTDEV_SKIP_CLAUDE_PREAPPROVE`, record onboarding, Remote Control, trust, and MCP approval                                             |
| `coder-agent-start.sh`                               | Coder `coder_script`            | the Coder agent's entry point: run `setup-gh-credential-helper.sh` (a failure only warns), then exec `claude-remote-control-start.sh`            |
| `claude-remote-control-start.sh`                     | `coder-agent-start.sh`, by hand | with a claude.ai login, run `claude /remote-control` in session `claude-remote` on the dedicated `tmux -L claude-remote` server                  |
| `setup-gh-credential-helper.sh`                      | start, `coder-agent-start.sh`   | `gh auth setup-git` when gh is logged in and no github.com helper exists                                                                         |
| `setup-keyring.sh`                                   | start                           | dbus + gnome-keyring session, persisted to `.tmp/keyring-session.env`                                                                            |
| `firewall.sh`                                        | start                           | run `init-firewall.sh` only when `ENABLE_FIREWALL=true`                                                                                          |
| `setup-git-safe-directory.sh`, `setup-pre-commit.sh` | start                           | `safe.directory`; hook install unless `AGENTDEV_SKIP_PRE_COMMIT`                                                                                 |
| `ci-hooks-repro.sh`                                  | by hand                         | run the hooks inside a bare `container:` job image to reproduce CI                                                                               |

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
sub-agent runs, outside this repository; it sets up the gh credential helper
with the agent's environment, where `GITHUB_TOKEN` is set, then execs the Remote
Control launcher. That launcher runs the session on its own tmux server, so the
Claude process inherits the caller's environment even when a default-socket
server is already live.

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
- `setup-gh-credential-helper.sh` sources `.tmp/keyring-session.env`, so it must
  run after `setup-keyring.sh`.
- `configure-codex.py` rewrites `config.toml` through `tomlkit`, keeping other
  tools' comments; keys it adds go above everything else in the file. Decision:
  [codex-full-access-in-devcontainer](../../architecture/codex-full-access-in-devcontainer.md).

## Key references

Verified anchor points (line numbers as of 2026-10-11):

- `.devcontainer/scripts/postCreateCommand.sh:56-62` — `~/.claude.json` symlink
  into the volume
- `.devcontainer/scripts/postCreateCommand.sh:67-68` — non-fatal CBM install
- `.devcontainer/scripts/postCreateCommand.sh:74` — Claude pre-approval
- `.devcontainer/scripts/postCreateCommand.sh:92-98` — staged-catalog install
- `.devcontainer/scripts/postStartCommand.sh:9-30` — the start sequence
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
- `.devcontainer/scripts/claude-remote-control-start.sh:12-27,38-39` — login
  gate, token-free launch on `tmux -L claude-remote`
- `.devcontainer/scripts/coder-agent-start.sh:9-13` — warn-only helper setup,
  exec of the Remote Control launcher
- `.devcontainer/scripts/setup-gh-credential-helper.sh:8,30` — keyring session
  load, `gh auth setup-git`
- `.devcontainer/scripts/configure-codex.py:29,46` — `render_config`,
  `write_atomically`
