# Dependency updates Specification

## Purpose

Defines what a Renovate change carries beyond the version it bumps: the
per-architecture checksums beside a pinned download, and the lock files and
pre-commit output the bump implies.

## Requirements

### Requirement: checksums move with their version

A bump of a pinned download that carries a per-architecture SHA-256 SHALL
recompute every architecture's checksum from the released asset and commit it in
the same change as the version.

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
imply, produced by the same toolchain contributors use.

#### Scenario: a bumped file needs formatting

- **WHEN** a pre-commit hook rewrites a file Renovate changed
- **THEN** the rewrite is part of Renovate's commit, not a follow-up push.

### Requirement: one post-upgrade task produces what a bump implies

`.github/renovate.json` SHALL declare one top-level `postUpgradeTasks` in
`branch` mode running `scripts/renovate-post-upgrade.py`, the only command
`renovate.yml` allows. The script SHALL refresh the checksums of every changed
pin file; when the `dev_tools` pins changed, SHALL fetch the pinned `iwe`,
verified against its recorded checksum, put it first on `PATH`, and run
`iwe normalize`; and SHALL then run `uv run --frozen pre-commit` on every
changed file, skipping `no-commit-to-branch`, accepting a first pass that only
rewrites files and failing when a hook still fails on the second. Any failure
SHALL fail the branch. `fileFilters` SHALL list every path a Renovate manager
edits plus the derived files.

#### Scenario: an iwe bump reformats the graph

- **WHEN** Renovate bumps the pinned `iwe` and the new release normalizes the
  graph differently
- **THEN** the branch's commit carries the graph as the new `iwe` normalizes it

#### Scenario: a hook keeps failing

- **WHEN** a pre-commit hook still fails on the second pass
- **THEN** the branch fails and no pull request carries the bump

### Requirement: CI never commits to a Renovate branch

No CI job SHALL push to a Renovate branch. On a Renovate pull request that
touches a tool-version owner, the `pre-commit` job SHALL run every hook on every
file and fail on whatever the post-upgrade pass missed.

#### Scenario: the post-upgrade pass missed a rewrite

- **WHEN** a Renovate pull request carries a file a hook would rewrite
- **THEN** the `pre-commit` job fails and pushes nothing

### Requirement: Renovate's token carries only the permissions it names

`renovate.yml` SHALL mint the Renovate App token with explicit permissions —
write on contents, pull requests, issues, workflows, checks, and statuses, and
read on administration and vulnerability alerts — rather than inheriting what
the App installation holds.

#### Scenario: the App gains a permission

- **WHEN** the App installation is granted a permission the workflow does not
  name
- **THEN** the token Renovate and its post-upgrade task run with lacks it

### Requirement: the Renovate config is validated at the bot's version

`.github/renovate.json` SHALL be validated with
`renovate-config-validator --no-global --strict` by a pre-commit hook and by
`validate-renovate-config.yml`, both at the Renovate release the hook's `bunx`
pin names, which SHALL be the release `renovate.yml` runs. The workflow SHALL
run in `agentdev-devcontainer` at the digest `devcontainer-compose-pins.yml`
pins, and its `Renovate config validation finished` check SHALL report on every
pull request.

#### Scenario: a repository config carries a global-only option

- **WHEN** `.github/renovate.json` sets a self-hosted global option such as
  `allowedCommands`
- **THEN** both the hook and the workflow fail

#### Scenario: Renovate bumps the Dev Container digest

- **WHEN** a pull request moves the pinned `agentdev-devcontainer` digest
- **THEN** the validation job runs inside the new image before the pull request
  can merge

### Requirement: apt packages install unpinned

The Ansible roles SHALL install apt packages by name, unpinned, from the
repositories each role enables. Every other tool a role fetches SHALL stay
pinned in the role's `defaults/` and kept current by Renovate.

#### Scenario: Ubuntu publishes a package update

- **WHEN** an image builds after Ubuntu updates a package a role installs
- **THEN** the image carries the updated package with no change in this
  repository

## Rationale

### One script behind one post-upgrade task

`postUpgradeTasks` is an object that a later matching `packageRule` replaces
rather than extends, so one script behind one task has no override ordering to
get wrong. Renovate commits its own edits first and keeps post-upgrade output
only where the path matches `fileFilters`, a file it edited itself included, so
a rewrite outside the filters is silently dropped. Renovate stops updating a
branch that carries a commit it did not author, which is why formatting must
arrive in its own commit and CI only reports. pre-commit runs through
`uv run --frozen`, never the image's unpinned apt `pre-commit`, so the pass
formats with the versions the bump pins. The image running the task still
carries the previous `iwe`, so the pinned one is fetched to apply the release
being pinned. The post-upgrade task runs freshly bumped code as Renovate's user,
which can reach Renovate's token; naming the permissions keeps a later App grant
from widening it.

Rejected:

- **A `postUpgradeTasks` per pin kind.** A later rule would silently drop the
  pre-commit step.
- **Skipping the lint gate on Renovate pull requests.** A gap in the
  post-upgrade pass would merge unnoticed.

### The config is validated at the bot's version

A mistyped option or an unparseable regex in `.github/renovate.json` fails
nothing at run time; it presents as updates that quietly stop arriving. One pin
serves hook, workflow, and bot, so the version that validates the config is the
version that reads it. Without `--no-global` the validator applies the
self-hosted global schema, which accepts options the repository schema rejects,
so the bot's global options live only in `renovate.yml`'s `RENOVATE_*`
environment. Running the workflow in the pinned image makes it the image canary:
a digest bump cannot automerge until the bot's toolchain runs in it. Neither
gate checks that a custom manager's `matchStrings` matches anything; that stays
a manual check.

### Apt packages stay unpinned

Each image is tied to one Ubuntu release by its base, which stays at 24.04
because downstream consumers depend on it, and within one release apt keeps its
packages mutually compatible. The accepted cost: two builds of one commit can
ship different apt versions, and an upstream regression cannot be bisected to a
change here.

Rejected:

- **Pin every apt package per Ubuntu release and architecture, kept current by
  Renovate.** Ubuntu drops a superseded version from `-updates` and `-security`,
  so pins rot and break the build until the next batch; every batch rebuilds the
  image; the refresh script and Renovate's `registryUrls` hold two unguarded
  copies of each role's repositories; roles become release- and
  architecture-specific; and dependency closures stay unpinned anyway.
