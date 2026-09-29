---
type: codebase
description: 'The postCreate, postStart, and postAttach hooks and the helpers they call: catalog reinstalls, codebase-memory-mcp wiring, uv sync, keyring, firewall gate, agent auth seeding and symlinks, gh credential helper, Claude Remote Control.'
source: .devcontainer/scripts
source_digest: sha256:f0a9c7ecedaa74bcc42d50cbdedf8d02da0a0a8775483029561689e08b61d495
verified:
  by: claude-code/opus-5
  at: 2026-09-29T12:30:00Z
stale_after: 2026-12-28
generated:
  by: claude-code/opus-5
  at: 2026-09-29T12:30:00Z
sources:
- id: code
  resource: .devcontainer/scripts
---

# Devcontainer lifecycle scripts

Twenty shell scripts, all `set -euo pipefail`, that the three lifecycle commands
in [devcontainer.json](../devcontainer.md) fan out to. Each resolves the
workspace from `DEV_WORKSPACE_FOLDER` with a `BASH_SOURCE` fallback so it also
runs outside the devcontainer.

## Public surface

| Script                                               | Called by             | Does                                                                                                                              |
| ---------------------------------------------------- | --------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `postCreateCommand.sh`                               | create (once)         | ownership fixes, `~/.claude.json` symlink, CBM install, auth dirs + seeding, Claude pre-approval, uv sync, staged-catalog install |
| `postStartCommand.sh`                                | every start           | CBM daemon + index, git safe.directory, auth seeding, pre-commit hooks, keyring, gh helper, firewall gate, Xpra, Remote Control   |
| `postAttachCommand.sh`                               | every editor attach   | CBM index, uv sync, reinstall the catalog from this checkout                                                                      |
| `reinstall-agentdev-claude.sh [root] [scope]`        | create, attach        | remove stale marketplaces for `root`, add it, install every published plugin at `scope`                                           |
| `reinstall-agentdev-codex.sh [root]`                 | create, attach        | the Codex equivalent, single-plugin; Codex has no scopes                                                                          |
| `codebase-memory-mcp-{install,start,index}.sh`       | create, start, attach | agent-config wiring, daemon start, repository index                                                                               |
| `uv-sync.sh`                                         | create, attach        | drop a managed `.venv` link, `uv sync --all-groups --all-extras` into `/uv`                                                       |
| `link-codex-auth.sh`                                 | create, start         | symlink `~/.codex/auth.json` into the shared auth volume                                                                          |
| `prepare-agent-auth-seed.sh`                         | `initializeCommand`   | write `AGENTDEV_CLAUDE_JSON`/`AGENTDEV_CODEX_JSON` as `0600` files in `AGENTDEV_AUTH_SEED_DIR`                                    |
| `seed-agent-auth.sh`                                 | create, start         | install each transfer file into an empty live credential, fix modes, delete the transfer file                                     |
| `preapprove-claude-workspace.sh`                     | create                | with `AGENTDEV_CLAUDE_AUTOSTART=1`, record onboarding, Remote Control, trust, and MCP approval                                    |
| `claude-remote-control-start.sh`                     | start                 | with `AGENTDEV_CLAUDE_AUTOSTART=1` and a login file, run `claude /remote-control` in tmux `claude-remote`                         |
| `setup-gh-credential-helper.sh`                      | start                 | `gh auth setup-git` when gh is logged in and no github.com helper exists                                                          |
| `setup-keyring.sh`                                   | start                 | dbus + gnome-keyring session, persisted to `.tmp/keyring-session.env`                                                             |
| `firewall.sh`                                        | start                 | run `init-firewall.sh` only when `ENABLE_FIREWALL=true`                                                                           |
| `setup-git-safe-directory.sh`, `setup-pre-commit.sh` | start                 | `safe.directory`; hook install unless `AGENTDEV_SKIP_PRE_COMMIT`                                                                  |
| `ci-hooks-repro.sh`                                  | by hand               | run the hooks inside a bare `container:` job image to reproduce CI                                                                |

## How it works

Create installs the image-staged catalog for both agents
(`AGENTDEV_CATALOG_DIR`, user scope for Claude); attach reinstalls from the
workspace with no argument, which defaults the root to this checkout and the
scope to `local`, so this repository develops the catalog in place while any
other project's attach finds no marketplace manifest and exits quietly. The
reinstall scripts list existing marketplaces whose path is the root, remove each
(uninstalling at every scope, tolerating "not found"), then add and install. The
Claude script reads every name from `.plugins[]` and loops, so the Claude
marketplace's two plugins both install; the Codex script reads `.plugins[0]`,
which is accurate because its manifest publishes one. CBM wiring temporarily
materializes the `~/.claude.json` symlink because the installer rewrites the
file.

Agent auth arrives as transfer files that `prepare-agent-auth-seed.sh` writes
from `initializeCommand`; `seed-agent-auth.sh` runs at create and at every
start, under a per-target `flock`, and copies a transfer file only into an
absent or empty live credential before deleting it. Behavior is specified in
[devcontainer-agent-auth](../../spec/devcontainer-agent-auth.md).

## Depends on

The image's tools (`claude`, `codex`, `codebase-memory-mcp`, `uv`, `jq`,
`gnome-keyring-daemon`) and the env variables the
[runtime contract](../api-image-runtime.md) lists. `uv-sync.sh` is also
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

## Key references

Verified anchor points (line numbers as of 2026-09-29):

- `.devcontainer/scripts/postCreateCommand.sh:56-62` — `~/.claude.json` symlink
  into the volume
- `.devcontainer/scripts/postCreateCommand.sh:72-73` — auth seeding and Claude
  pre-approval
- `.devcontainer/scripts/postCreateCommand.sh:91-94` — staged-catalog install
- `.devcontainer/scripts/postStartCommand.sh:9-31` — the start sequence
- `.devcontainer/scripts/postAttachCommand.sh:14-15` — workspace reinstall
- `.devcontainer/scripts/reinstall-agentdev-claude.sh:74-76` — add + install
- `.devcontainer/scripts/reinstall-agentdev-codex.sh:64-65` — add + install
- `.devcontainer/scripts/codebase-memory-mcp-install.sh:55-75` — symlink
  materialization and restore
- `.devcontainer/scripts/uv-sync.sh:23-32` — managed-link removal and sync
- `.devcontainer/scripts/seed-agent-auth.sh:6,22,47` — `seed_credential`, the
  per-target lock, the atomic install
- `.devcontainer/scripts/claude-remote-control-start.sh:9,31` — login-file gate,
  token-free launch
- `.devcontainer/scripts/setup-gh-credential-helper.sh:13,32` — keyring session
  load, `gh auth setup-git`
