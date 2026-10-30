---
type: feature
stage: accepted
description: One zsh bootstrap script in the agentdev catalog turns a stock macOS host into one that runs agentdev natively — the catalog's CLI tools through Homebrew, a uv-provisioned Python first on PATH, pinned release-only tools, and the agentdev plugin.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T16:18:33Z
sources:
- resource: docs/knowledge/data/plans/20261013-macos-native-bootstrap.md
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
- It keeps one marker-delimited block in `~/.zprofile` so every new login shell
  resolves `env python3` to the uv-provisioned Python.
- It installs the `agentdev` plugin into Claude Code, and into Codex when its
  CLI is present, unless `--skip-plugins` is passed.
- It prints each tool's version and exits non-zero naming whatever failed.

## Edge cases

- **Not macOS.** The script refuses to run.
- **No Homebrew.** The script prints Homebrew's install command and stops; it
  never drives the interactive `sudo` that installing Homebrew needs.
- **Re-run.** The `~/.zprofile` block is rewritten in place, never duplicated.

## Open questions

None — the plan settles the design.

## References

- Plan: [Bootstrap agentdev natively on macOS with
  Homebrew](../plans/20261013-macos-native-bootstrap.md)
