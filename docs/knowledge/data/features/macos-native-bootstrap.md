---
type: feature
stage: accepted
description: One zsh bootstrap script in the agentdev catalog turns a stock macOS host into one that runs agentdev natively — the catalog's CLI tools through Homebrew, a uv-provisioned Python first on PATH, pinned release-only tools, and the agentdev plugin.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T23:34:07Z
sources:
- resource: docs/knowledge/data/plans/20261013-macos-native-bootstrap.md
- resource: .agents/plugins/agentdev/bin/macos-bootstrap.zsh
---

# Native macOS bootstrap

## Purpose

The agentdev catalog is provisioned only by the runtime images. A macOS host
that runs agents natively — for example a macOS guest used as the isolation
boundary so Xcode and the iOS Simulator are reachable — has no provisioning
path: its stock `python3` is older than the catalog's scripts need, and the
tools the skills call are absent.

## Behaviour

**`bin/macos-bootstrap.zsh`** in the agentdev catalog runs on a stock macOS host
with Homebrew, first through `curl -fsSL <raw URL> | zsh` and later from `PATH`
once the plugin is enabled. Each run is idempotent:

- It installs `uv`, `jq`, `gh`, `shellcheck`, `bun`, `pre-commit`, and Claude
  Code through Homebrew, at floating versions.
- It installs, through uv, the Python version the catalog is tested on as the
  default `python3`.
- It installs `iwe` and `codebase-memory-mcp` from their release tarballs at the
  versions the image pins, each checked against a recorded SHA-256.
- It keeps one marker-delimited block in `~/.zprofile` so every new zsh login
  shell resolves `env python3` to the uv-provisioned Python. When fish is
  installed or is the user's `$SHELL`, it keeps the same kind of block in
  `~/.config/fish/conf.d/agentdev.fish`, which runs `brew shellenv` for fish and
  then puts `~/.local/bin` ahead of it with `fish_add_path`.
- It installs the `agentdev` plugin into Claude Code, the only agent it
  configures, unless `--skip-plugins` is passed.
- It prints each tool's version, checks that a fresh zsh login shell — and a
  fresh login shell of the user's `$SHELL` when that is not zsh — resolves
  `python3` to the uv-provisioned Python, and exits non-zero naming whatever
  failed.

## Edge cases

- **Not macOS.** The script refuses to run.
- **No Homebrew.** The script prints Homebrew's install command and stops; it
  never drives the interactive `sudo` that installing Homebrew needs.
- **Re-run.** Each marker block is rewritten in place, never duplicated.
- **No fish.** When fish is neither on `PATH` nor the user's `$SHELL`, no fish
  configuration is written.
- **Another `python3` in the user's shell.** When the user's `$SHELL` resolves
  `python3` somewhere other than the uv-provisioned Python — another shell with
  no block, or a later configuration that puts another `python3` first — the
  script exits non-zero naming that shell's check.

## Open questions

None — the plan settles the design.

## References

- Plan: [Bootstrap agentdev natively on macOS with
  Homebrew](../plans/20261013-macos-native-bootstrap.md)
