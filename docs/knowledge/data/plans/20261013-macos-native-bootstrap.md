---
type: plan
created: 2026-10-13
release:
- features/macos-native-bootstrap
description: A zsh bootstrap in the agentdev catalog's bin/ that turns a stock macOS host into one that runs agentdev without a devcontainer — Homebrew tools including uv, a uv-provisioned Python first on PATH, pinned release-only tools, and the agentdev plugin.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T21:27:47Z
sources:
- resource: .agents/plugins/agentdev/bin
- resource: ansible/roles/dev_tools/defaults/main.yml
- resource: ansible/roles/agentic_tools/tasks/install_catalog.yml
- resource: pyproject.toml
- resource: .pre-commit-config.yaml
- resource: .github/workflows/validate-agent-files.yml
- resource: .agents/AGENTS.md
- resource: docs/knowledge/data/plans/20261029-catalog-scripts-python.md
- resource: https://docs.astral.sh/uv/concepts/python-versions/
- resource: docs/knowledge/data/plans/20261031-remove-codex.md
---

# Bootstrap agentdev natively on macOS with Homebrew

## Context

The agentdev catalog is provisioned only by the runtime images: their tools come
from apt-based Ansible roles and the plugin is installed from the image-staged
catalog. Running agents natively on macOS — for example inside a UTM macOS guest
that serves as the isolation boundary in place of the devcontainer, so that
Xcode and the iOS Simulator are directly reachable — has no provisioning path at
all.

[Port the catalog's bundled shell scripts to
Python](20261029-catalog-scripts-python.md) ships first and makes every catalog
script stdlib-only Python on `#!/usr/bin/env python3`. Two gaps then block a
stock macOS host:

- The catalog is tested only on the Python version the root `pyproject.toml`'s
  `requires-python` names. A stock host's `/usr/bin/python3` is a shim that
  installs the Xcode Command Line Tools through a dialog and then provides
  Python 3.9.
- The tools the catalog calls — `gh`, `jq`, `shellcheck`, `uv`, `bun`,
  `pre-commit`, `iwe`, `codebase-memory-mcp` — and the agent CLIs that install
  the plugin are absent.

Claude Code is the agent CLI the bootstrap provisions: [Remove Codex
support](20261031-remove-codex.md) drops Codex from the supported harnesses.

## Approach

Add `bin/macos-bootstrap.zsh` to the agentdev catalog. It is a single
self-contained zsh file, so a first run works through
`curl -fsSL <raw URL> | zsh` before the plugin exists, using the `/bin/zsh`
every supported macOS ships, and once the plugin is enabled the same script is
on `PATH` for re-runs. Steps, each idempotent:

1. Refuse to run on anything but Darwin; require `brew` and print Homebrew's
   official install command when it is absent.
2. `brew bundle --file=-` with an inline Brewfile: formulae `uv`, `jq`, `gh`,
   `shellcheck`, `bun`, `pre-commit`, and cask `claude-code`. Versions float;
   only the tools in steps 3 and 4 are pinned.
3. `uv python install <version> --default`, which places a `python3` executable
   in uv's executable directory, `~/.local/bin`. `<version>` is recorded in the
   script.
4. Install the tools Homebrew lacks — `iwe` with `iwes`, and
   `codebase-memory-mcp` — from their GitHub release darwin tarballs into
   `~/.local/bin`, at the same versions `ansible/roles/dev_tools` pins, each
   verified against a SHA-256 recorded in the script per architecture. `iwec`
   stays uninstalled even though the iwe tarball ships it, matching the image
   ([IWE through the CLI, not MCP](../architecture/iwe-cli-over-mcp.md)).
5. Write a marker-delimited block to `~/.zprofile` that evaluates
   `brew shellenv` and prepends `~/.local/bin`, so `env python3` resolves to the
   uv-provisioned Python in every new login shell. Rewrite the block in place on
   re-run; never duplicate it.
6. Unless `--skip-plugins` is passed: register the
   `plume-works/agent-devcontainer` GitHub marketplace in Claude Code at user
   scope and install `agentdev` only. Codex is never touched, even when its CLI
   is on `PATH`.
7. Verify: print each tool's version, confirm the `python3` a fresh login shell
   resolves reports the recorded version, and exit nonzero naming whatever
   failed.

zsh sits outside the repository's shell convention, which requires bash and
`shellcheck`, and `shellcheck` cannot parse zsh. The bootstrap is checked with
`zsh -n` and kept out of the `shellcheck` hook, and root `AGENTS.md` and the
catalog-script-language architecture document record it as the catalog's one
non-Python script, because it runs before anything is installed.

Rejected: a bash bootstrap that also installs Homebrew bash 5, because no
catalog script needs bash once the Python port has shipped; Homebrew's `python`
formula, because uv provisions the exact version the catalog is tested on and is
already a required tool; a `macos/` Template-class directory at the repository
root, which would reach only template consumers who copy it, whereas the catalog
reaches every plugin user; and pinning brew formulae to the image versions,
which would mean replacing Homebrew with release tarballs for every tool.

Assumptions:

- The Brewfile is inline in the script rather than a sibling file, so one `curl`
  fetches everything.
- Homebrew itself is not installed by the script; installing it needs an
  interactive `sudo` the script should not drive.
- The bootstrap is a user-run command, not a skill script, so it does not adopt
  the `RESULT=` contract — it must run before the catalog is on disk.
- The plugin step covers Claude Code only and installs `agentdev` only. The user
  decided both; Claude Code only follows [Remove Codex
  support](20261031-remove-codex.md).
- The recorded Python version is the lower bound of the root `pyproject.toml`'s
  `requires-python`, the oldest version the repository's own tests run the
  catalog on.
- uv's `--default` install of the `python3` executable works without
  `--preview`; Task 3's macOS run confirms it.

## Implementation Steps

### Task 1: Failing tests for the bootstrap's logic

**Files:** Create: `.agents/plugins/agentdev/tests/test_macos_bootstrap.py`,
`scripts/tests/test_macos_bootstrap_pins.py`

The plugin test resolves the script through the `plugin_root` fixture and runs
it with `zsh`, skipping when `zsh` is absent, as it is in the Linux images; the
macOS job in Task 3 runs it. Stub `uname`, `brew`, `uv`, `curl`, `shasum`,
`claude`, and `codex` as executables on a temporary `PATH`, each logging its
arguments; point `HOME` at a temporary directory.

- [x] A non-Darwin `uname` exits nonzero before any `brew` call.
  - **Evidence:** commit `031b7ec0` adds
    `test_non_darwin_exits_before_any_installer` in
    `.agents/plugins/agentdev/tests/test_macos_bootstrap.py`; red against the
    missing script:
    `uv run pytest .agents/plugins/agentdev/tests/test_macos_bootstrap.py scripts/tests/test_macos_bootstrap_pins.py`
    → 3 failed, 11 errors.
- [x] A missing `brew` exits nonzero and prints the Homebrew install command.
  - **Evidence:** commit `031b7ec0` adds
    `test_missing_brew_prints_install_command_and_changes_nothing` in
    `.agents/plugins/agentdev/tests/test_macos_bootstrap.py`; red against the
    missing script:
    `uv run pytest .agents/plugins/agentdev/tests/test_macos_bootstrap.py scripts/tests/test_macos_bootstrap_pins.py`
    → 3 failed, 11 errors.
- [x] `brew bundle --file=-` receives every formula and the `claude-code` cask
  on stdin.
  - **Evidence:** commit `031b7ec0` adds
    `test_brew_bundle_receives_every_formula_and_the_claude_code_cask` in
    `.agents/plugins/agentdev/tests/test_macos_bootstrap.py`; red against the
    missing script:
    `uv run pytest .agents/plugins/agentdev/tests/test_macos_bootstrap.py scripts/tests/test_macos_bootstrap_pins.py`
    → 3 failed, 11 errors.
- [x] `uv python install` receives the recorded version and `--default`.
  - **Evidence:** commit `031b7ec0` adds
    `test_uv_installs_the_recorded_python_as_default` in
    `.agents/plugins/agentdev/tests/test_macos_bootstrap.py`; red against the
    missing script:
    `uv run pytest .agents/plugins/agentdev/tests/test_macos_bootstrap.py scripts/tests/test_macos_bootstrap_pins.py`
    → 3 failed, 11 errors.
- [x] A release tarball whose checksum does not match is rejected and nothing
  lands in `~/.local/bin`.
  - **Evidence:** commit `031b7ec0` adds
    `test_checksum_mismatch_rejects_the_archive` in
    `.agents/plugins/agentdev/tests/test_macos_bootstrap.py`; red against the
    missing script:
    `uv run pytest .agents/plugins/agentdev/tests/test_macos_bootstrap.py scripts/tests/test_macos_bootstrap_pins.py`
    → 3 failed, 11 errors.
- [x] From an iwe archive that holds `iwe`, `iwes`, and `iwec`, only `iwe` and
  `iwes` land in `~/.local/bin`.
  - **Evidence:** commit `031b7ec0` adds
    `test_only_iwe_and_iwes_are_installed_from_the_iwe_archive` in
    `.agents/plugins/agentdev/tests/test_macos_bootstrap.py`; red against the
    missing script:
    `uv run pytest .agents/plugins/agentdev/tests/test_macos_bootstrap.py scripts/tests/test_macos_bootstrap_pins.py`
    → 3 failed, 11 errors.
- [x] Two runs leave exactly one marker block in `~/.zprofile`, and existing
  content outside it is preserved byte-for-byte.
  - **Evidence:** commit `031b7ec0` adds
    `test_rerun_keeps_one_marker_block_and_preserves_other_content` in
    `.agents/plugins/agentdev/tests/test_macos_bootstrap.py`; red against the
    missing script:
    `uv run pytest .agents/plugins/agentdev/tests/test_macos_bootstrap.py scripts/tests/test_macos_bootstrap_pins.py`
    → 3 failed, 11 errors.
- [x] The plugin step adds the marketplace and installs `agentdev` and never
  `self-improve`; `--skip-plugins` makes no `claude` or `codex` call; no `codex`
  call happens when `codex` is absent from `PATH`.
  - **Evidence:** commit `031b7ec0` adds
    `test_plugin_step_installs_only_agentdev`,
    `test_plugin_step_includes_codex_when_present`, and
    `test_skip_plugins_calls_neither_agent_plugin_command` in
    `.agents/plugins/agentdev/tests/test_macos_bootstrap.py`; red against the
    missing script:
    `uv run pytest .agents/plugins/agentdev/tests/test_macos_bootstrap.py scripts/tests/test_macos_bootstrap_pins.py`
    → 3 failed, 11 errors.
- [x] In `scripts/tests/test_macos_bootstrap_pins.py` (repository-level, because
  the Ansible defaults and the root `pyproject.toml` do not ship with the
  plugin): the release versions in the script equal the `iwe` and
  `codebase-memory-mcp` versions in `ansible/roles/dev_tools/defaults/main.yml`,
  and the recorded Python version equals the lower bound of `requires-python`,
  each read from its file rather than restated.
  - **Evidence:** commit `031b7ec0` adds `test_iwe_matches_the_image_pin`,
    `test_codebase_memory_mcp_matches_the_image_pin`, and
    `test_python_is_the_requires_python_floor`, reading `dev_tools` through
    `yaml` and `pyproject.toml` through `tomllib`; red against the missing
    script in the same run.

### Task 2: Implement `bin/macos-bootstrap.zsh`

**Files:** Create: `.agents/plugins/agentdev/bin/macos-bootstrap.zsh`; Modify:
`.pre-commit-config.yaml`, `AGENTS.md`, `.agents/AGENTS.md`

- [x] The seven steps in `## Approach`, with darwin `arm64` and `amd64` SHA-256
  values for the `iwe` and `codebase-memory-mcp` versions `dev_tools` pins at
  implementation time, taken from the published release assets.
  - **Evidence:** commit `470a78dd` adds
    `.agents/plugins/agentdev/bin/macos-bootstrap.zsh`; its four SHA-256 values
    equal the GitHub release asset digests for `iwe-v0.29.3` and `v0.12.1`
    (`gh release view --json assets`), whose Linux digests match the `dev_tools`
    checksums.
- [x] Task 1's tests pass:
  `uv run pytest .agents/plugins/agentdev/tests/test_macos_bootstrap.py scripts/tests/test_macos_bootstrap_pins.py`.
  - **Evidence:** at commit `470a78dd`, the command → 14 passed under zsh 5.9;
    the full plugin suite `uv run pytest .agents/plugins/agentdev/tests` → 435
    passed.
- [x] `zsh -n .agents/plugins/agentdev/bin/macos-bootstrap.zsh` passes, and
  `pre-commit run shellcheck --files .agents/plugins/agentdev/bin/macos-bootstrap.zsh`
  does not lint it, with an `exclude` on the hook if it would.
  - **Evidence:** commit `470a78dd` adds the `exclude` to the `shellcheck` hook,
    which otherwise fails with SC1071; at that commit `zsh -n` passes and the
    hook reports `(no files to check)Skipped`.
- [x] Root `AGENTS.md`'s Shell convention names the bootstrap as the one zsh
  script and why it is zsh, and `.agents/AGENTS.md`'s rule that every `bin/`
  script is Python names it as the exception.
  - **Evidence:** commit `470a78dd` edits root `AGENTS.md` `### Shell` and the
    `bin/` language rule in `.agents/AGENTS.md`.

### Task 3: Run the bootstrap on a macOS CI runner

**Files:** Modify: `.github/workflows/validate-agent-files.yml`

- [x] Add a `macos-bootstrap` job on `macos-latest`, gated by the existing
  `paths-filter`, that runs the script with `/bin/zsh`, then from a fresh login
  `zsh` runs `git-new-branch.py --help` to show a catalog script runs on the
  provisioned Python, and runs Task 1's plugin test file with pytest through uv.
  Pass `--skip-plugins` only if the plugin commands need authentication, and
  record that in `## Verification results`.
  - **Evidence:** commit `09e79dd4` adds the job to
    `.github/workflows/validate-agent-files.yml`, and commit `fc11e146` makes
    the script's `~/.zprofile` rewrite work with macOS awk; Actions run
    41241447306 (job `macOS native bootstrap`) runs the bootstrap without
    `--skip-plugins` — the plugin commands needed no authentication — then
    `git-new-branch.py --help` on `/Users/runner/.local/bin/python3` (Python
    3.12.15) and the plugin test file (11 passed).

### Task 4: Green macOS CI run

- [x] The `macos-bootstrap` job passes on the pull request.
  - **Evidence:** on PR #601 at commit `fc11e146`, Actions run 41241447306's
    `macOS native bootstrap` job concluded `success`.

### Task 5: Document the native macOS path

**Files:** Modify: `.agents/plugins/agentdev/README.md`,
`docs/knowledge/data/architecture/template-boundary.md`,
`docs/knowledge/data/architecture/catalog-script-language.md`

- [x] The catalog README gains a "Native macOS" section: the one-line
  `curl -fsSL <raw URL> | zsh` invocation, what the script changes on the host
  (`~/.zprofile`, `~/.local/bin`, Homebrew packages, the uv-managed Python,
  plugin install), and `--skip-plugins`.
  - **Evidence:** commit `c8b1d7ac` adds `## Native macOS` to
    `.agents/plugins/agentdev/README.md`;
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    → 0 errors, 0 warnings.
- [x] `template-boundary` states that a native macOS host consumes the catalog
  only, provisioned by `bin/macos-bootstrap.zsh`, and that the `.devcontainer/`
  runtime surface does not apply to it.
  - **Evidence:** commit `c8b1d7ac` adds `## Native macOS host` to
    `data/architecture/template-boundary`; `iwe normalize` and
    `iwe schema validate` pass.
- [x] `catalog-script-language` records the bootstrap as the catalog's one
  non-Python script and the reason.
  - **Evidence:** commit `c8b1d7ac` adds `## The one non-Python script` to
    `data/architecture/catalog-script-language` and names the exception in its
    description and `## Decision`; `iwe schema validate` passes.

### Task 6: Drop the Codex plugin step

**Files:** Modify: `.agents/plugins/agentdev/bin/macos-bootstrap.zsh`,
`.agents/plugins/agentdev/tests/test_macos_bootstrap.py`,
`.agents/plugins/agentdev/README.md`

- [ ] `install_plugins` makes no `codex` call even when `codex` is on `PATH`;
  `test_plugin_step_includes_codex_when_present` is replaced by a test that
  stubs `codex` on `PATH` and asserts the script never invokes it.
- [ ] The script's `--help` text and the README's "Native macOS" section name
  Claude Code as the only agent the plugin step installs into.
- [ ] Task 1's tests pass:
  `uv run pytest .agents/plugins/agentdev/tests/test_macos_bootstrap.py scripts/tests/test_macos_bootstrap_pins.py`.

### Task 7: Green macOS CI run without Codex

- [ ] The `macos-bootstrap` job passes on the pull request at a commit that
  includes Task 6.

## Spec changes

Creates `spec/macos-native-bootstrap`:

``` markdown
## ADDED Requirements

### Requirement: the bootstrap provisions a stock macOS host for agentdev

`bin/macos-bootstrap.zsh` SHALL run under macOS's `/bin/zsh`, SHALL refuse any
OS other than Darwin, and SHALL install through Homebrew `uv`, `jq`, `gh`,
`shellcheck`, `bun`, `pre-commit`, and the `claude-code` cask. It SHALL NOT
install Homebrew itself.

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

### Requirement: login shells resolve the provisioned tools first

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
that a fresh login shell resolves `python3` to the recorded version, and SHALL
exit nonzero naming each check that failed.

#### Scenario: The stock Python still comes first on PATH

- **WHEN** a fresh login shell resolves `python3` to `/usr/bin/python3`
- **THEN** the script exits nonzero and names the Python check
```

## Depends on

[Port the catalog's bundled shell scripts to
Python](20261029-catalog-scripts-python.md)

## Verification

- `uv run pytest .agents/plugins/agentdev/tests/test_macos_bootstrap.py scripts/tests/test_macos_bootstrap_pins.py`
  passes.
- `zsh -n .agents/plugins/agentdev/bin/macos-bootstrap.zsh` passes.
- The `macos-bootstrap` job in `validate-agent-files.yml` passes on the pull
  request.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Installing Homebrew bash or Homebrew's `python` formula.
- Docker, Super-Linter, and `microvm-sandbox` on macOS; the existing
  `remote-codespace-session` escalation covers hosts without Docker.
- The MCP gateway sidecar, the egress firewall, git SSH signing, and the keyring
  the devcontainer lifecycle sets up.
- Installing `self-improve`.
- Installing `iwec` or registering an IWE MCP server in Claude Code.
- Installing the plugin into any agent CLI other than Claude Code.
- Xcode, Expo, and iOS Simulator setup.
- Renovate automation for the script's release pins; the Task 1 sync test turns
  an image-only bump into a failing test instead.

## Key references

Verified anchor points (line numbers as of 2026-10-31):

- `pyproject.toml:4` — `requires-python = ">=3.12"`, the recorded Python version
- `ansible/roles/dev_tools/defaults/main.yml:58` — `iwe` entry (`iwe-v0.29.3`,
  `binaries: [iwe, iwes]` at `:63`)
- `ansible/roles/dev_tools/defaults/main.yml:84` — `codebase-memory-mcp` entry
  (`v0.12.1`)
- `ansible/roles/agentic_tools/tasks/install_catalog.yml:9` — the staged Claude
  marketplace manifest, the image's equivalent of the plugin step
- `.github/workflows/validate-agent-files.yml:20` — `paths-filter` job; `:52`
  `validate-agent-files` job; `:78` agentdev plugin test step; `:102`
  `macos-bootstrap` job
- `.pre-commit-config.yaml:51` — the `shellcheck` hook
- `AGENTS.md:95` — the Shell convention: bash and `shellcheck`
- `.agents/plugins/agentdev/README.md:109` — `bin/` is on `PATH` while the
  plugin is enabled; `:60` — `## Native macOS`, whose `:84` names Codex
- `docs/knowledge/data/architecture/template-boundary.md:284` — Publisher-only
  source section listing `.agents/`; `:273` — `## Native macOS host`
- `.agents/AGENTS.md:16` — plugin tests must pass from a consumer's plugin
  cache, resolving scripts through `plugin_root`; `:36` — every `bin/` and
  `agent-code/` script is standard-library-only Python
- `.agents/plugins/agentdev/bin/macos-bootstrap.zsh:111` — `install_plugins`;
  `:120` — its Codex branch
- `.agents/plugins/agentdev/tests/test_macos_bootstrap.py:71` — `CODEX_STUB`;
  `:292` — `test_plugin_step_includes_codex_when_present`; `:304` —
  `test_skip_plugins_calls_neither_agent_plugin_command`
