---
type: codebase
description: 'The postCreate, postStart, and postAttach hooks and the helpers they call: catalog reinstalls, codebase-memory-mcp wiring, uv sync, keyring, firewall gate, agent auth seeding and symlinks, gh credential helper, Claude Remote Control, Codex policy.'
source: .devcontainer/scripts
source_digest: sha256:cd25f1bdf3fc55b099a28d970b3e8b84152d0306cf4e5a292f2e1683510d6b59
verified:
  by: claude-code/opus-5.5
  at: 2026-10-09T18:00:00Z
stale_after: 2027-01-07
generated:
  by: claude-code/opus-5.5
  at: 2026-10-09T18:00:00Z
sources:
- id: code
  resource: .devcontainer/scripts
---

# Devcontainer lifecycle scripts

Twenty-two shell scripts, all `set -euo pipefail`, and one `uv run --script`
Python script that the three lifecycle commands in
[devcontainer.json](../devcontainer.md) fan out to. Each resolves the workspace
from `DEV_WORKSPACE_FOLDER` with a `BASH_SOURCE` fallback so it also runs
outside the devcontainer.

## Public surface

| Script                                               | Called by             | Does                                                                                                                                                        |
| ---------------------------------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `postCreateCommand.sh`                               | create (once)         | ownership fixes, `~/.claude.json` symlink, CBM install, auth dirs + seeding, Claude pre-approval, uv sync, staged-catalog install                           |
| `postStartCommand.sh`                                | every start           | CBM daemon + index, git safe.directory, auth seeding, pre-commit hooks, keyring, gh helper, firewall gate, Xpra, Remote Control, Codex auth link and policy |
| `postAttachCommand.sh`                               | every editor attach   | CBM index, uv sync, reinstall the catalog from this checkout                                                                                                |
| `reinstall-agentdev-claude.sh [root] [scope]`        | create, attach        | remove stale marketplaces for `root`, add it, install every published plugin at `scope`                                                                     |
| `reinstall-agentdev-codex.sh [root]`                 | create, attach        | the Codex equivalent, single-plugin; Codex has no scopes                                                                                                    |
| `reinstall-agentdev-opencode.sh [root]`              | create, attach        | point the `plugin` list of the user's `opencode.json` at `root`'s OpenCode bridge, replacing any earlier bridge entry                                       |
| `codebase-memory-mcp-{install,start,index}.sh`       | create, start, attach | agent-config wiring, daemon start, repository index                                                                                                         |
| `uv-sync.sh`                                         | create, attach        | drop a managed `.venv` link, `uv sync --all-groups --all-extras` into `/uv`                                                                                 |
| `link-codex-auth.sh`                                 | create, start         | symlink `~/.codex/auth.json` into the shared auth volume                                                                                                    |
| `configure-codex.py`                                 | start (last)          | set top-level `sandbox_mode` and `approval_policy` in `${CODEX_HOME:-~/.codex}/config.toml`, atomically at `0600`                                           |
| `prepare-agent-auth-seed.sh`                         | `initializeCommand`   | write `AGENTDEV_CLAUDE_JSON`/`AGENTDEV_CODEX_JSON` as `0600` files in `AGENTDEV_AUTH_SEED_DIR`                                                              |
| `workspace-seed-key.sh <path>`                       | `initializeCommand`   | print the per-workspace seed key, a 16-hex sha256 prefix, via `sha256sum` or `shasum`                                                                       |
| `seed-agent-auth.sh`                                 | create, start         | install each transfer file into an empty live credential, fix modes, delete the transfer file                                                               |
| `preapprove-claude-workspace.sh`                     | create                | with `AGENTDEV_CLAUDE_AUTOSTART=1`, record onboarding, Remote Control, trust, and MCP approval                                                              |
| `claude-remote-control-start.sh`                     | start                 | with `AGENTDEV_CLAUDE_AUTOSTART=1` and a login file, run `claude /remote-control` in tmux `claude-remote`                                                   |
| `setup-gh-credential-helper.sh`                      | start                 | `gh auth setup-git` when gh is logged in and no github.com helper exists                                                                                    |
| `setup-keyring.sh`                                   | start                 | dbus + gnome-keyring session, persisted to `.tmp/keyring-session.env`                                                                                       |
| `firewall.sh`                                        | start                 | run `init-firewall.sh` only when `ENABLE_FIREWALL=true`                                                                                                     |
| `setup-git-safe-directory.sh`, `setup-pre-commit.sh` | start                 | `safe.directory`; hook install unless `AGENTDEV_SKIP_PRE_COMMIT`                                                                                            |
| `ci-hooks-repro.sh`                                  | by hand               | run the hooks inside a bare `container:` job image to reproduce CI                                                                                          |

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
symlink because the installer rewrites the file.

Agent auth arrives as transfer files that `prepare-agent-auth-seed.sh` writes
from `initializeCommand`; `seed-agent-auth.sh` runs at create and at every
start, under a per-target `flock`, and copies a transfer file only into an
absent or empty live credential before deleting it. Behavior is specified in
[devcontainer-agent-auth](../../spec/devcontainer-agent-auth.md).

## Depends on

The image's tools (`claude`, `codex`, `codebase-memory-mcp`, `uv`, `jq`,
`gnome-keyring-daemon`) and the env variables the [runtime
contract](../api-image-runtime.md) lists. `uv-sync.sh` is also
`.devcontainer/scripts/uv-sync.sh` in the repository's own instructions.

## Invariants & gotchas

- `CBM_CACHE_DIR` unset is a hard failure in every CBM script; a missing binary
  is a soft skip.
- `ENABLE_FIREWALL=true` with no `init-firewall.sh` in the image exits 1.
- A CI `container:` job supplies none of `devcontainer.json`'s env or mounts;
  `ci-hooks-repro.sh` exists because that difference is invisible from inside a
  devcontainer.
- `uv-sync.sh` removes only a `.venv` symlink pointing into `/uv/venvs/`; a
  foreign `.venv` is left alone with a warning.
- A non-empty live credential always wins over a seed; the seeder only corrects
  its mode.
- The Remote Control launcher never passes `CLAUDE_CODE_OAUTH_TOKEN` to `claude`
  and skips startup without a login file.
- `setup-gh-credential-helper.sh` sources `.tmp/keyring-session.env`, so it must
  run after `setup-keyring.sh`.
- `configure-codex.py` rewrites `config.toml` through `tomlkit`, keeping other
  tools' comments; keys it adds go above everything else in the file. Decision:
  [codex-full-access-in-devcontainer](../../architecture/codex-full-access-in-devcontainer.md).

## Key references

Verified anchor points (line numbers as of 2026-10-09):

- `.devcontainer/scripts/postCreateCommand.sh:56-62` — `~/.claude.json` symlink
  into the volume
- `.devcontainer/scripts/postCreateCommand.sh:72-73` — auth seeding and Claude
  pre-approval
- `.devcontainer/scripts/postCreateCommand.sh:91-95` — staged-catalog install
- `.devcontainer/scripts/postStartCommand.sh:9-34` — the start sequence
- `.devcontainer/scripts/postAttachCommand.sh:14-16` — workspace reinstall
- `.devcontainer/scripts/reinstall-agentdev-claude.sh:74-76` — add + install
- `.devcontainer/scripts/reinstall-agentdev-codex.sh:64-65` — add + install
- `.devcontainer/scripts/reinstall-agentdev-codex.sh:69-76` — Codex agent
  install, skipped for a catalog without the installer
- `.devcontainer/scripts/reinstall-agentdev-opencode.sh:32-38` — bridge entry
  rewrite
- `.devcontainer/scripts/codebase-memory-mcp-install.sh:55-75` — symlink
  materialization and restore
- `.devcontainer/scripts/uv-sync.sh:23-32` — managed-link removal and sync
- `.devcontainer/scripts/seed-agent-auth.sh:6,25,50` — `seed_credential`, the
  per-target lock, the atomic install
- `.devcontainer/scripts/claude-remote-control-start.sh:9,31` — login-file gate,
  token-free launch
- `.devcontainer/scripts/setup-gh-credential-helper.sh:11,30` — keyring session
  load, `gh auth setup-git`
- `.devcontainer/scripts/configure-codex.py:29,46` — `render_config`,
  `write_atomically`
