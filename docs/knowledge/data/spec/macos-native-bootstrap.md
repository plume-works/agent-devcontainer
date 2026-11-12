---
type: spec
description: How the agentdev catalog's bin/macos-bootstrap.zsh provisions a stock macOS host — Homebrew tools, a uv-provisioned Python first on PATH, pinned checksum-verified release tools, login-shell PATH blocks, the agentdev plugin in Claude Code, and a final check.
sources:
- resource: .agents/plugins/agentdev/bin/macos-bootstrap.zsh
- resource: .agents/plugins/agentdev/tests/test_macos_bootstrap.py
- resource: scripts/tests/test_refresh_pin_checksums.py
- resource: .github/renovate.json
- resource: .github/workflows/validate-agent-files.yml
- resource: docs/knowledge/data/plans/20261013-macos-native-bootstrap.md
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

#### Scenario: Piped from its raw URL

- **WHEN** the script is run as `curl -fsSL <raw URL> | zsh`
- **THEN** no command it runs consumes the rest of the script from standard
  input
- **AND** it provisions the host as when run from a file

#### Scenario: Homebrew is missing

- **WHEN** `brew` is not on `PATH`
- **THEN** the script exits nonzero and prints Homebrew's install command
- **AND** it changes nothing on the host

#### Scenario: Not macOS

- **WHEN** `uname -s` is not `Darwin`
- **THEN** the script exits nonzero before running any installer

### Requirement: uv provisions the catalog's Python

The script SHALL install, through uv, the Python version it records, as the
default `python3` executable in `~/.local/bin`.

#### Scenario: Only the stock Python is present

- **WHEN** the host's only `python3` is `/usr/bin/python3`
- **THEN** after the script runs, `python3 --version` in a fresh login shell
  reports the recorded version

### Requirement: release-only tools are pinned and checksum-verified

The script SHALL install `iwe` and `iwes` into `~/.local/bin` from their GitHub
release darwin archive, at the version `ansible/roles/dev_tools` pins, which
Renovate moves in the same pull request, and SHALL verify the archive's SHA-256
before installing anything from it. It SHALL NOT install `iwec`.

#### Scenario: Checksum mismatch

- **WHEN** a downloaded archive's SHA-256 differs from the recorded value
- **THEN** the script exits nonzero
- **AND** no binary from that archive is installed

#### Scenario: The iwe archive ships an MCP server

- **WHEN** the iwe archive contains `iwe`, `iwes`, and `iwec`
- **THEN** `iwe` and `iwes` are installed
- **AND** `iwec` is not

### Requirement: login shells resolve the provisioned tools first

The script SHALL maintain exactly one marker-delimited block in `~/.zprofile`
that evaluates `brew shellenv` and prepends `~/.local/bin`, rewriting it in
place on re-run and leaving all content outside it unchanged. When `fish` is on
`PATH` or is the user's `$SHELL`, the script SHALL maintain the same kind of
block in `~/.config/fish/conf.d/agentdev.fish`, running `brew shellenv` for fish
and then `fish_add_path` for `~/.local/bin`.

#### Scenario: Re-run

- **WHEN** the script runs twice
- **THEN** `~/.zprofile` holds one marker block
- **AND** content outside the block is unchanged

#### Scenario: fish is installed

- **WHEN** `fish` is on `PATH` and the script runs twice
- **THEN** `~/.config/fish/conf.d/agentdev.fish` holds one marker block that
  puts `~/.local/bin` ahead of Homebrew's `bin`
- **AND** content outside the block is unchanged

#### Scenario: fish is absent

- **WHEN** `fish` is not on `PATH` and `$SHELL` is zsh
- **THEN** the script does not create `~/.config/fish/conf.d/agentdev.fish`

### Requirement: only the agentdev plugin is installed

Unless `--skip-plugins` is given, the script SHALL register the
`plume-works/agent-devcontainer` marketplace and install `agentdev` at user
scope in Claude Code. It SHALL NOT install `self-improve`, and SHALL NOT invoke
`codex`.

#### Scenario: Plugins skipped

- **WHEN** the script runs with `--skip-plugins`
- **THEN** it does not invoke `claude`

#### Scenario: Codex is installed

- **WHEN** `codex` is on `PATH`
- **THEN** the script installs `agentdev` in Claude Code
- **AND** it does not invoke `codex`

### Requirement: the bootstrap verifies its result

The script SHALL finish by reporting each installed tool's version and checking
that a fresh zsh login shell, and a fresh login shell of the user's `$SHELL`
when that is not zsh, resolve `python3` to the recorded version in
`~/.local/bin`, and SHALL exit nonzero naming each check that failed.

#### Scenario: The stock Python still comes first on PATH

- **WHEN** a fresh login shell resolves `python3` to `/usr/bin/python3`
- **THEN** the script exits nonzero and names the Python check

#### Scenario: The user's shell resolves another Python

- **WHEN** `$SHELL` is not zsh and its fresh login shell resolves `python3`
  outside `~/.local/bin`
- **THEN** the script exits nonzero and names that shell's Python check
