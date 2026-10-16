---
type: plan
created: 2026-10-13
release:
- features/macos-native-bootstrap
description: A Homebrew-based bootstrap in the agentdev catalog's bin/ that turns a stock macOS host into one that runs agentdev without a devcontainer — bash 5 first on PATH, the catalog's CLI tools, pinned release-only tools, and the agentdev plugin.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-15T00:00:00Z
sources:
- resource: .agents/plugins/agentdev/bin
- resource: ansible/roles/dev_tools/defaults/main.yml
- resource: .devcontainer/scripts/reinstall-agentdev-claude.sh
- resource: .devcontainer/scripts/reinstall-agentdev-codex.sh
- resource: .github/workflows/validate-agent-files.yml
- resource: .agents/AGENTS.md
---

# Bootstrap agentdev natively on macOS with Homebrew

## Context

The agentdev catalog is provisioned only by the `agent-desktop` image: its tools
come from apt-based Ansible roles and the plugin is installed from the
image-staged `/opt/agentdev`. Running agents natively on macOS — for example
inside a UTM macOS guest that serves as the isolation boundary in place of the
devcontainer, so that Xcode and the iOS Simulator are directly reachable — has
no provisioning path at all.

Two gaps block it on a stock macOS host:

- macOS ships bash 3.2 at `/bin/bash`. Catalog scripts start with
  `#!/usr/bin/env bash` and three of them use bash 4 builtins (`mapfile`,
  `declare -A`), so they fail unless a newer bash precedes `/bin` on `PATH`.
- The tools skills call — `gh`, `jq`, `shellcheck`, `uv`, `bun`, `pre-commit`,
  `iwe`, `codebase-memory-mcp` — and the agent CLIs that install the plugin are
  absent.

## Approach

Add `bin/macos-bootstrap.sh` to the agentdev catalog. It is a single
self-contained file, so a first run works through `curl -fsSL <raw URL> | bash`
before the plugin exists, and once the plugin is enabled the same script is on
`PATH` for re-runs. Steps, each idempotent:

1. Refuse to run on anything but Darwin; require `brew` and print Homebrew's
   official install command when it is absent.
2. `brew bundle --file=-` with an inline Brewfile: formulae `bash`, `jq`, `gh`,
   `shellcheck`, `uv`, `bun`, `pre-commit`, and cask `claude-code`. Versions
   float; only the release-only tools in step 3 are pinned.
3. Install the tools Homebrew lacks — `iwe` with `iwes`, and
   `codebase-memory-mcp` — from their GitHub release darwin tarballs into
   `~/.local/bin`, at the same versions `ansible/roles/dev_tools` pins, each
   verified against a SHA-256 recorded in the script per architecture. `iwec`
   stays uninstalled even though the iwe tarball ships it, matching the image
   ([IWE through the CLI, not MCP](../architecture/iwe-cli-over-mcp.md)).
4. Write a marker-delimited block to `~/.zprofile` that evaluates
   `brew shellenv` and prepends `~/.local/bin`, so `env bash` resolves to
   Homebrew's bash 5 in every new login shell. Rewrite the block in place on
   re-run; never duplicate it.
5. Unless `--skip-plugins` is passed: register the
   `plume-works/agent-devcontainer` GitHub marketplace in Claude Code at user
   scope and install `agentdev` only; when `codex` is on `PATH`, do the
   equivalent for Codex.
6. Verify: print each tool's version, confirm the `bash` a fresh login shell
   resolves reports major version ≥ 4, and exit nonzero naming whatever failed.

The script itself runs under `/bin/bash` 3.2 on a first run, so it uses no bash
4 constructs.

Rejected: a `macos/` Template-class directory at the repository root. It would
reach only template consumers who copy it, whereas the catalog reaches every
plugin user and keeps the bootstrap versioned with the scripts it makes
runnable. Rejected: pinning brew formulae to the image versions — it would mean
replacing Homebrew with release tarballs for every tool.

Assumptions:

- The Brewfile is inline in the script rather than a sibling file, so one `curl`
  fetches everything.
- Homebrew itself is not installed by the script; installing it needs an
  interactive `sudo` the script should not drive.
- The bootstrap is a user-run command, not a skill script, so it does not adopt
  the `RESULT=` contract or source `result-codes.sh` — it must run before the
  catalog is on disk.
- Codex gets the same `agentdev` install when its CLI is present. The user
  decided the plugin step covers Claude Code, plus Codex when present, and
  installs `agentdev` only.

## Implementation Steps

### Task 1: Failing tests for the bootstrap's logic

**Files:** Create: `.agents/plugins/agentdev/tests/test_macos_bootstrap.py`,
`scripts/tests/test_macos_bootstrap_pins.py`

The plugin test resolves the script through the `plugin_root` fixture. Stub
`uname`, `brew`, `curl`, `shasum`, `claude`, and `codex` as executables on a
temporary `PATH`, each logging its arguments; point `HOME` at a temporary
directory.

- [ ] A non-Darwin `uname` exits nonzero before any `brew` call.
- [ ] A missing `brew` exits nonzero and prints the Homebrew install command.
- [ ] `brew bundle --file=-` receives every formula and the `claude-code` cask
  on stdin.
- [ ] A release tarball whose checksum does not match is rejected and nothing
  lands in `~/.local/bin`.
- [ ] From an iwe archive that holds `iwe`, `iwes`, and `iwec`, only `iwe` and
  `iwes` land in `~/.local/bin`.
- [ ] Two runs leave exactly one marker block in `~/.zprofile`, and existing
  content outside it is preserved byte-for-byte.
- [ ] The plugin step adds the marketplace and installs `agentdev` and never
  `self-improve`; `--skip-plugins` makes no `claude` or `codex` call; no `codex`
  call happens when `codex` is absent from `PATH`.
- [ ] In `scripts/tests/test_macos_bootstrap_pins.py` (repository-level, because
  the Ansible defaults do not ship with the plugin): the release versions in the
  script equal the `iwe` and `codebase-memory-mcp` versions in
  `ansible/roles/dev_tools/defaults/main.yml`, read from that file rather than
  restated.
- [ ] The script contains no bash 4 constructs (`mapfile`, `readarray`,
  `declare -A`, `local -A`, `${var,,}`, `${var^^}`, `|&`, `&>>`).

### Task 2: Implement `bin/macos-bootstrap.sh`

**Files:** Create: `.agents/plugins/agentdev/bin/macos-bootstrap.sh`

- [ ] The six steps in `## Approach`, with darwin `arm64` and `amd64` SHA-256
  values for `iwe-v0.26.1` and `codebase-memory-mcp` `v0.11.0` taken from the
  published release assets.
- [ ] Task 1's tests pass:
  `uv run pytest .agents/plugins/agentdev/tests/test_macos_bootstrap.py scripts/tests/test_macos_bootstrap_pins.py`.
- [ ] `shellcheck` passes on the script.

### Task 3: Run the bootstrap on a macOS CI runner

**Files:** Modify: `.github/workflows/validate-agent-files.yml`

- [ ] Add a `macos-bootstrap` job on `macos-latest`, gated by the existing
  `paths-filter`, that runs the script with `/bin/bash`, then runs
  `git-new-branch.sh --help` from a fresh login `zsh` to show a bash 4 script
  now runs. Pass `--skip-plugins` only if the plugin commands need
  authentication, and record that in `## Verification results`.

### Task 4: Green macOS CI run

- [ ] The `macos-bootstrap` job passes on the pull request.

### Task 5: Document the native macOS path

**Files:** Modify: `.agents/plugins/agentdev/README.md`,
`docs/knowledge/data/architecture/template-boundary.md`

- [ ] The catalog README gains a "Native macOS" section: the one-line `curl`
  invocation, what the script changes on the host (`~/.zprofile`,
  `~/.local/bin`, Homebrew packages, plugin install), and `--skip-plugins`.
- [ ] `template-boundary` states that a native macOS host consumes the catalog
  only, provisioned by `bin/macos-bootstrap.sh`, and that the `.devcontainer/`
  runtime surface does not apply to it.

### Task 6: Refresh the codebase map docs

**Files:** Modify:
`docs/knowledge/data/codebase/agents/plugins/agentdev/bin.md`,
`docs/knowledge/data/codebase/agents/plugins/agentdev/tests.md`

- [ ] Refresh both with `/agentdev:iwe-map` so `stale-map-docs.py` passes.

## Spec changes

Creates `spec/macos-native-bootstrap`:

``` markdown
## ADDED Requirements

### Requirement: the bootstrap provisions a stock macOS host for agentdev

`bin/macos-bootstrap.sh` SHALL run under macOS's `/bin/bash` 3.2, SHALL refuse
any OS other than Darwin, and SHALL install through Homebrew `bash`, `jq`, `gh`,
`shellcheck`, `uv`, `bun`, `pre-commit`, and the `claude-code` cask. It SHALL
NOT install Homebrew itself.

#### Scenario: Homebrew is missing

- **WHEN** `brew` is not on `PATH`
- **THEN** the script exits nonzero and prints Homebrew's install command
- **AND** it changes nothing on the host

#### Scenario: Not macOS

- **WHEN** `uname -s` is not `Darwin`
- **THEN** the script exits nonzero before running any installer

### Requirement: release-only tools are pinned and checksum-verified

The script SHALL install `iwe`, `iwes`, and `codebase-memory-mcp` into
`~/.local/bin` from their GitHub release darwin archives, at the versions
`ansible/roles/dev_tools` pins, and SHALL verify each archive's SHA-256 before
installing anything from it. It SHALL NOT install `iwec`.

#### Scenario: Checksum mismatch

- **WHEN** a downloaded archive's SHA-256 differs from the recorded value
- **THEN** the script exits nonzero
- **AND** no binary from that archive is installed

#### Scenario: The iwe archive ships an MCP server

- **WHEN** the iwe archive contains `iwe`, `iwes`, and `iwec`
- **THEN** `iwe` and `iwes` are installed
- **AND** `iwec` is not

### Requirement: bash 5 precedes /bin on PATH in login shells

The script SHALL maintain exactly one marker-delimited block in `~/.zprofile`
that evaluates `brew shellenv` and prepends `~/.local/bin`, rewriting it in place
on re-run and leaving all content outside it unchanged.

#### Scenario: Re-run

- **WHEN** the script runs twice
- **THEN** `~/.zprofile` holds one marker block
- **AND** content outside the block is unchanged

### Requirement: only the agentdev plugin is installed

Unless `--skip-plugins` is given, the script SHALL register the
`plume-works/agent-devcontainer` marketplace and install `agentdev` at user
scope in Claude Code, and in Codex when its CLI is on `PATH`. It SHALL NOT
install `self-improve`.

#### Scenario: Plugins skipped

- **WHEN** the script runs with `--skip-plugins`
- **THEN** it invokes neither `claude` nor `codex`

### Requirement: the bootstrap verifies its result

The script SHALL finish by reporting each installed tool's version and checking
that a fresh login shell resolves `bash` to major version 4 or later, and SHALL
exit nonzero naming each check that failed.

#### Scenario: Old bash still first on PATH

- **WHEN** a fresh login shell resolves `bash` to version 3.2
- **THEN** the script exits nonzero and names the bash check
```

## Verification

- `uv run pytest .agents/plugins/agentdev/tests/test_macos_bootstrap.py scripts/tests/test_macos_bootstrap_pins.py`
  passes.
- `shellcheck .agents/plugins/agentdev/bin/macos-bootstrap.sh` is clean.
- The `macos-bootstrap` job in `validate-agent-files.yml` passes on the pull
  request.
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py` passes.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Porting the catalog's bash 4 scripts to bash 3.2; the bootstrap makes bash 5
  available instead.
- Docker, Super-Linter, and `microvm-sandbox` on macOS; the existing
  `remote-codespace-session` escalation covers hosts without Docker.
- The MCP gateway sidecar, the egress firewall, git SSH signing, and the keyring
  the devcontainer lifecycle sets up.
- Installing `self-improve`.
- Installing `iwec` or registering an IWE MCP server in Claude Code or Codex.
- Xcode, Expo, and iOS Simulator setup.
- Renovate automation for the script's release pins; the Task 1 sync test turns
  an image-only bump into a failing test instead.

## Key references

Verified anchor points (line numbers as of 2026-10-15):

- `.agents/plugins/agentdev/bin/shellcheck-fix.sh:9` — `mapfile -d ''`, a bash 4
  builtin
- `.agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.sh:247`
  — `declare -A changed_between`
- `.agents/plugins/agentdev/skills/template-consume/agent-code/check-updates.sh:178`
  — `mapfile -t tracked_paths`; `:180` `declare -A seen_changed_paths`
- `ansible/roles/dev_tools/defaults/main.yml:32` — `iwe` entry (`iwe-v0.26.1`,
  `binaries: [iwe, iwes]` at `:37`)
- `ansible/roles/dev_tools/defaults/main.yml:58` — `codebase-memory-mcp` entry
  (`v0.11.0`)
- `.devcontainer/scripts/reinstall-agentdev-claude.sh:74` —
  `claude plugin marketplace add`; `:76` `claude plugin install`
- `.devcontainer/scripts/reinstall-agentdev-codex.sh:16` — Codex marketplace
  manifest path `.agents/plugins/marketplace.json`
- `.github/workflows/validate-agent-files.yml:20` — `paths-filter` job; `:62`
  `validate-agent-files` job; `:83` agentdev plugin test step
- `docs/knowledge/data/codebase/agents/plugins/agentdev.md:57` — `bin/` is on
  `PATH` while the plugin is enabled
- `docs/knowledge/data/architecture/template-boundary.md:253` — Publisher-only
  source section listing `.agents/`
- `.agents/AGENTS.md:16` — plugin tests must pass from a consumer's plugin
  cache, resolving scripts through `plugin_root`
