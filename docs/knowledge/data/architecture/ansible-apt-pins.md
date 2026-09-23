---
type: architecture
description: Why the Ansible roles install apt packages at an exact version from a generated per-release, per-architecture pin file, and what that costs.
generated:
  by: claude-code/opus-5
  at: 2026-09-22T00:00:00Z
sources:
- resource: ansible/roles
- resource: scripts/apt-pins-refresh.py
- resource: .github/renovate.json
- resource: https://github.com/Dr-QP/Dr.QP/pull/494
---

# Ansible apt pins

## Decision

Every apt package an Ansible role installs is pinned to an exact version in
`ansible/roles/<role>/vars/apt_pins_<suite>_<arch>.yml`. The role loads the file
matching `system_dist` and `system_arch` and hands apt the `name=version` list
it holds. Renovate maintains the values through two `deb` custom managers, one
per architecture, batched into a single automerged pull request.

An unpinned `apt install` lets the Ubuntu archive and every third-party
repository decide what the image contains, so two builds of the same commit are
not the same image and a regression cannot be bisected to a change here. Pinning
moves that decision into reviewable, revertable files.

## Per release and per architecture

The file name carries both because the version a package resolves to is specific
to both. Ubuntu serves `amd64` from `archive.ubuntu.com` and `arm64` from
`ports.ubuntu.com`, and a package can be published for one architecture before
the other; CI builds both natively. A consuming project on a different Ubuntu
release adds its own `apt_pins_<suite>_<arch>.yml` — without one, the role fails
on the missing file rather than installing something unpinned.

## The pin wins in both directions

Every pinned install sets `allow_downgrade: true`. `ansible.builtin.apt` refuses
a downgrade by default, so without it a role could not converge to its own pin
on a host carrying a newer version — which is the state every warm build is in
after a reverted bump, and the state CI's own base image is in whenever a batch
is reverted. A pin that only ever moves forward is not a pin; it is a floor.

The cost is that reverting a pin to a version with a known defect downgrades
silently rather than failing loudly. That is accepted: the revert is explicit in
the diff, and the alternative makes reverts impossible rather than merely
visible.

## Repository sets

A pin is only installable from a repository the role actually enables, so each
role resolves against its own set. Most roles see the four Ubuntu pockets and
nothing else. Five see more: `cmake_kitware` and `dev_tools` (Kitware, which
publishes the `cmake` both install), `dev_tools` again (the git-core PPA it
adds), `github_cli` (the GitHub CLI repository, whose suite is `stable`),
`install_docker` (Docker's own), and `nodejs` (NodeSource, whose suite is
`nodistro` and whose URL carries the Node major).

That set is written down twice — `ROLE_REPOS` in `scripts/apt-pins-refresh.py`
and the `registryUrls` package rules in `.github/renovate.json` — and the two
must agree. When they disagree the script and Renovate propose different
versions and revert each other. Nothing enforces the agreement today.

## What this costs

**A pin can become unfetchable.** Ubuntu drops a version from `-updates` or
`-security` as soon as it is superseded, so a pin rots the moment upstream
republishes, and the image build fails until the next batch merges — up to a day
at the current schedule. Docker, NodeSource and Kitware keep their history, so
those pins do not rot.

**Every merged batch rebuilds the image.** The pin files live under `ansible/`,
inside the CI image path filter, so one batch a day is one multi-arch rebuild a
day. Tightening the schedule shortens the breakage window and buys more builds;
the two move together and the schedule is the only dial.

**Only the named packages are pinned.** Their dependency closures still resolve
to whatever apt picks, so the image is reproducible in what the roles ask for,
not in every byte it installs.

## Alternatives considered

**Pinning from the published image's `dpkg` status** rather than from the
current indices. It reproduces the shipped image exactly, but a version that is
installed is not necessarily still downloadable — the `-updates` pocket carries
one version per package. Resolving from the indices guarantees the pin is
fetchable when it lands, at the cost of not being a byte-for-byte reproduction
of the previous image.

**A checksum beside each version**, as the direct binary downloads in
`dev_tools` carry. Apt already verifies package integrity against a signed
repository index, so a checksum would add nothing and, because Renovate cannot
update one, would leave every automerged bump with a stale hash. The same
reasoning shapes the pins that do carry checksums —
[Renovate maintains checksum-carrying pins](../features/renovate-maintains-checksums.md).

**Pinning in `defaults/` beside the tool version pins**, where a consuming
project could override them. Rejected: a consumer overriding one package version
out of a resolved set gets a combination nothing has built, and the file is
generated, so an override would be rewritten on the next refresh.

## Key references

Verified anchor points (line numbers as of 2026-09-22):

- `scripts/apt-pins-refresh.py:73-81` — `ROLE_REPOS`, the per-role repository
  sets the Renovate `registryUrls` rules must mirror
- `ansible/roles/cmake_kitware/tasks/main.yml:3-5` — the `include_vars` every
  pinned role opens with
- `ansible/roles/.agent.metadata.json` — the digest mask that keeps an
  automerged pin bump from marking the Ansible map docs stale
