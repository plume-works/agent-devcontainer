---
type: spec
description: How self-hosted Renovate keeps checksums, lock files, and pre-commit output in the same change as the version bump that implies them, how its configuration is validated at the version the bot runs, and which dependencies are deliberately left unpinned.
sources:
- resource: .github/workflows/validate-renovate-config.yml
- resource: .github/actions/paths-filter/action.yml
- resource: .pre-commit-config.yaml
- resource: scripts/fetch-pinned-tool.py
- resource: ansible/roles/cmake_kitware/tasks/main.yml
- resource: .github/renovate.json
- resource: .github/workflows/renovate.yml
- resource: scripts/renovate-post-upgrade.py
- resource: scripts/refresh-pin-checksums.py
- resource: scripts/tests/test_refresh_pin_checksums.py
- resource: scripts/tests/test_renovate_post_upgrade.py
---

# Dependency updates

## Purpose

Defines what a Renovate change carries beyond the version it bumps: the
per-architecture checksums beside a pinned download, and the lock files and
pre-commit output the bump implies.

## Requirements

### Requirement: checksums move with their version

A bump of a pinned download that carries a per-architecture SHA-256 SHALL
recompute every architecture's checksum from the released asset and commit it in
the same change as the version. The asset SHALL be fetched from the URL its
consumer's own template renders — the `dev_tools` install task, a
`*_download_url` default, or the macOS bootstrap's `install_release` calls — and
only pin files registered in `scripts/refresh-pin-checksums.py::PIN_FILES` are
refreshed. The `ansible role dependency pins` group SHALL move a tool's
`dev_tools` and macOS bootstrap pins in one pull request.

#### Scenario: a checksum-carrying pin is bumped

- **WHEN** Renovate raises a pinned version whose asset carries checksums
- **THEN** the pull request carries the new version and a checksum for every
  architecture computed from the new asset.

#### Scenario: an asset cannot be fetched

- **WHEN** any architecture's asset fails to download during the refresh
- **THEN** Renovate fails the branch and commits no version change.

#### Scenario: a tag moves under an unchanged version

- **WHEN** a pin whose version did not change hashes differently than its
  recorded checksum
- **THEN** the refresh fails and the recorded checksum is kept.

### Requirement: derived files are regenerated with the bump

A Renovate change SHALL carry the lock files and pre-commit output its edits
imply, produced by the same toolchain contributors use. `.github/renovate.json`
SHALL declare one top-level `postUpgradeTasks` in `branch` mode running
`scripts/renovate-post-upgrade.py`, and `renovate.yml` SHALL allow exactly that
command. The script SHALL refresh checksums first; when the `dev_tools` pins
changed, it SHALL run `iwe normalize` with the newly pinned `iwe`, verified
against its recorded checksum and first on `PATH` for the hooks after it; then
it SHALL run `uv run --frozen pre-commit` on every changed file, skipping
`no-commit-to-branch`, accepting a first pass that only rewrites files and
failing on a hook that still fails on the second. Any failure SHALL fail the
branch. The task's `fileFilters` SHALL match every path a Renovate manager in
this repository edits and every file the task derives, because Renovate keeps
post-upgrade output only where it matches them.

#### Scenario: a bumped file needs formatting

- **WHEN** a pre-commit hook rewrites a file Renovate changed
- **THEN** the rewrite is part of Renovate's commit, not a follow-up push.

#### Scenario: Renovate bumps `iwe`

- **WHEN** a Renovate branch moves the `iwe` pin in
  `ansible/roles/dev_tools/defaults/main.yml`
- **THEN** the branch carries the graph as the new `iwe` normalizes it, and the
  `iwe` hooks run at the new version.

#### Scenario: a hook fails twice

- **WHEN** a pre-commit hook still fails on the post-upgrade task's second pass
- **THEN** Renovate fails the branch and commits no version change.

### Requirement: Renovate's token carries only Renovate's permissions

`renovate.yml` SHALL request its GitHub App token with an explicit permission
set — write on contents, pull requests, issues, workflows, checks, and statuses,
and read on administration and vulnerability alerts — rather than everything the
App installation holds.

#### Scenario: the App is granted a new permission

- **WHEN** the App installation gains a permission `renovate.yml` does not name
- **THEN** the token Renovate and its post-upgrade task run with does not carry
  it.

### Requirement: the Renovate config is validated at the bot's version

`.github/renovate.json` SHALL be validated with
`renovate-config-validator --no-global --strict` by a pre-commit hook and by
`validate-renovate-config.yml`, both at the Renovate release the hook's
`bunx --package renovate@<version>` entry names, and `renovate.yml` SHALL run
the bot at that same release. The bot's global options SHALL come from
`RENOVATE_*` environment variables, never a checked-in config file. A
`custom.regex` manager SHALL track the pin.
`Renovate config validation finished` SHALL report on every pull request, and
its validation job SHALL run when a change touches the config,
`.pre-commit-config.yaml`, `devcontainer-compose-pins.yml`, the workflow, or the
image's sources.

#### Scenario: the config carries a global-only option

- **WHEN** `.github/renovate.json` sets an option only the self-hosted global
  config accepts, such as `allowedCommands`
- **THEN** the hook and the workflow fail.

#### Scenario: Renovate bumps its own pin

- **WHEN** a pull request moves the `renovate@<version>` pin
- **THEN** the validation job runs at the new version before the pull request
  can merge, and the next bot run uses it.

#### Scenario: a pull request touches nothing the check covers

- **WHEN** a pull request changes none of the paths the filter lists
- **THEN** the validation job is skipped and
  `Renovate config validation finished` passes.

### Requirement: apt packages are unpinned within the base release

The Ansible roles SHALL install apt packages by name, with no version, from the
repositories each role enables, and `cmake_kitware` SHALL upgrade an existing
Kitware `cmake` to the newest one Kitware publishes. Renovate SHALL NOT bump the
base's Ubuntu release.

#### Scenario: Ubuntu publishes a package update

- **WHEN** an image is built after Ubuntu updates a package a role installs
- **THEN** the image carries the updated package with no change to this
  repository.

## Rationale

### One post-upgrade task behind one script

`postUpgradeTasks` is an object that a later matching `packageRule` replaces
rather than extends, so one script behind one top-level task has no override
ordering to get wrong. pre-commit runs through `uv run`, never the image's
unpinned apt copy, so the pass formats with the versions the bump pins: `uv run`
syncs the environment to a bumped `uv.lock` before pre-commit starts. The image
the task runs in still carries the previous `iwe`, so a release that migrates
`.iwe/config.toml` or reformats the graph is applied by the version being
pinned. Renovate stops updating a branch that carries a commit it did not
author, so the formatting a bump implies must arrive in Renovate's own commit;
CI's pre-commit job never pushes a fix and instead fails a Renovate pull request
whose post-upgrade pass missed something. The post-upgrade task runs code at
just-bumped versions as the same user as Renovate, which is why the App token
names its permissions instead of inheriting the installation's.

Rejected:

- **A `postUpgradeTasks` per pin kind.** A checksum rule would silently replace
  the pre-commit step.
- **Skipping the lint gate on Renovate pull requests.** Keeps Renovate's
  branches free of foreign commits just as well, but a gap in the post-upgrade
  pass would merge unnoticed.

### Renovate's config is validated by the version that reads it

Nothing else checks the config before it reaches the bot, and a mistyped option
or an unparseable custom-manager regex presents as updates that quietly stop
arriving. One pin serves hook, workflow, and bot. `--no-global` is passed
because the validator's default applies the self-hosted global schema, which
accepts and rejects a different set of options than the repository schema
Renovate reads for this file; `--strict` also fails on warnings and on a config
needing migration. Both gates check that the config is valid, not that a custom
manager's `matchStrings` extracts anything.

Rejected:

- **Baking Renovate into the agentdev-devcontainer image.** Still one pin, and
  it brings a large Node dependency tree into every developer's image for the
  rare commit that touches `.github/renovate.json`; `bunx` fetches the pinned
  release per run instead.

### apt packages float within a fixed Ubuntu release

Version pinning holds for everything else the roles fetch — the downloaded
binaries and the installer- and registry-sourced tools in each role's
`defaults/`. Each image is tied to Ubuntu 24.04 by its base, and within one
release apt keeps its packages mutually compatible, so a fixed base already
bounds what an unpinned install can change. Another Ubuntu release ships as a
separately named image tag. The accepted cost: two builds of one commit can ship
different apt versions, and a regression from an upstream package update cannot
be bisected to a change in this repository.

Rejected:

- **Pinning every apt package per Ubuntu release and architecture**, in
  generated per-role pin files kept current by Renovate `deb` managers in one
  batched daily pull request. Ubuntu drops a superseded version from `-updates`
  and `-security`, so a pin becomes unfetchable and the build fails until the
  next batch merges; every batch is a multi-arch rebuild because the pin files
  sit under `ansible/`; each role's repository set would be listed twice, in the
  refresh script and Renovate's `registryUrls`, with nothing keeping them in
  agreement; a consumer on another release or architecture fails on the missing
  pin file; and the dependency closures of the pinned packages still float.
