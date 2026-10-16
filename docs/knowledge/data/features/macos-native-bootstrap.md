---
type: feature
stage: accepted
description: One Homebrew-based bootstrap script in the agentdev catalog turns a stock macOS host into one that runs agentdev natively — bash 5 first on PATH, the catalog's CLI tools, pinned release-only tools, and the agentdev plugin.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-16T12:00:00Z
sources:
- resource: docs/knowledge/data/plans/20261013-macos-native-bootstrap.md
---

# Native macOS bootstrap

## Purpose

The agentdev catalog is provisioned only by the `agent-desktop` image. A macOS
host that runs agents natively — for example a macOS guest used as the isolation
boundary so Xcode and the iOS Simulator are reachable — has no provisioning
path: it ships bash 3.2, and the tools the skills call are absent.

## Behaviour

**`bin/macos-bootstrap.sh`** in the agentdev catalog runs on a stock macOS host
with Homebrew, first through `curl -fsSL <raw URL> | bash` and later from `PATH`
once the plugin is enabled. Each run is idempotent:

- It installs bash, `jq`, `gh`, `shellcheck`, `uv`, `bun`, `pre-commit`, and
  Claude Code through Homebrew, at floating versions.
- It installs `iwe` and `codebase-memory-mcp` from their release tarballs at the
  versions the image pins, each checked against a recorded SHA-256.
- It keeps one marker-delimited block in `~/.zprofile` so every new login shell
  resolves `env bash` to bash 5.
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
