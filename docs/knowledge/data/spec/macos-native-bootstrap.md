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

### Requirement: login shells resolve the provisioned tools first

The script SHALL maintain exactly one marker-delimited block in `~/.zprofile`
that evaluates `brew shellenv` and prepends `~/.local/bin`, rewriting it in
place on re-run and leaving all content outside it unchanged. When `fish` is on
`PATH` or is the user's `$SHELL`, the script SHALL maintain the same kind of
block in `~/.config/fish/conf.d/agentdev.fish`, running `brew shellenv` for fish
and then `fish_add_path` for `~/.local/bin`. A `$SHELL` other than zsh or fish
SHALL get no block, so the final check names that shell rather than reporting a
`PATH` the user's terminal does not have.

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

#### Scenario: The user's shell is neither zsh nor fish

- **WHEN** `$SHELL` is bash and no bash configuration puts `~/.local/bin` first
- **THEN** the script writes no bash `PATH` block, exits nonzero, and names the
  bash Python check

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
