---
type: spec
description: How the agentdev catalog's bin/macos-bootstrap.zsh provisions a stock macOS host — Homebrew tools, a uv-provisioned Python first on PATH, pinned checksum-verified release tools, login-shell PATH blocks, the agentdev plugin in Claude Code, and a final check.
sources:
- resource: .agents/plugins/agentdev/bin/macos-bootstrap.zsh
- resource: .agents/plugins/agentdev/tests/test_macos_bootstrap.py
- resource: scripts/tests/test_refresh_pin_checksums.py
- resource: .github/renovate.json
- resource: .github/workflows/validate-agent-files.yml
- resource: pyproject.toml
---

# macOS native bootstrap

## Purpose

`bin/macos-bootstrap.zsh` in the agentdev catalog turns a stock macOS host with
Homebrew into one that runs agentdev natively, without a devcontainer.

## Requirements

### Requirement: the bootstrap provisions a stock macOS host for agentdev

`bin/macos-bootstrap.zsh` SHALL run under macOS's `/bin/zsh`, SHALL refuse any
OS other than Darwin, and SHALL install through Homebrew `uv`, `jq`, `gh`,
`shellcheck`, `bun`, `pre-commit`, and the `claude-code` cask, at whatever
version Homebrew currently ships, with no version pinned. It SHALL NOT install
Homebrew itself. It SHALL run the same whether started from a file or piped into
zsh from its raw URL (`curl -fsSL <raw URL> | zsh`): its commands SHALL read
standard input from `/dev/null`, never from the pipe that carries the script.

#### Scenario: Homebrew is missing

- **WHEN** `brew` is not on `PATH`
- **THEN** the script exits nonzero and prints Homebrew's install command
- **AND** it changes nothing on the host

#### Scenario: Not macOS

- **WHEN** `uname -s` is not `Darwin`
- **THEN** the script exits nonzero before running any installer

## Rationale

### Homebrew tools float; uv pins the catalog's Python

Homebrew versions float, and only the uv Python and the release-only tools are
pinned. The recorded Python version is the lower bound of the root
`pyproject.toml`'s `requires-python`, the oldest version the repository's tests
run the catalog on; a stock host's `/usr/bin/python3` (Xcode Command Line Tools)
is older than that floor. The script does not install Homebrew, because that
needs an interactive `sudo` it should not drive. The Brewfile is inline so one
`curl` fetches everything. Shell configuration that later puts another `python3`
first is the user's to fix; the final check surfaces it.

Rejected:

- **Homebrew's `python` formula.** uv provisions the exact version the catalog
  is tested on and is already required.
- **A `macos/` Template-class directory at the repository root.** It reaches
  only template consumers who copy it, while the catalog reaches every plugin
  user.
- **Pinning Homebrew formulae to the image's versions.** It would mean replacing
  Homebrew with release tarballs for every tool.

### The bootstrap provisions only what agentdev runs natively

The bootstrap sets up no Docker, Super-Linter, or `microvm-sandbox`, no MCP
gateway, git SSH signing, or keyring, and no Xcode, Expo, or iOS Simulator, and
it does not install fish.
