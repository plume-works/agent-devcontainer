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
