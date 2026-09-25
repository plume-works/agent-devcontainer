---
type: architecture
description: Why the Ansible roles install apt packages unpinned, and why per-release, per-architecture apt pin files maintained by Renovate were rejected.
generated:
  by: claude-code/opus-5.5
  at: 2026-09-25T00:00:00Z
sources:
- resource: ansible/roles
- resource: .github/renovate.json
---

# Ansible apt pins

## Decision

The Ansible roles install apt packages by name, unpinned: each role lists its
packages inline in its `ansible.builtin.apt` task, and apt installs whatever the
repositories the role enables serve at build time. `cmake_kitware` upgrades an
existing Kitware `cmake` to the newest one Kitware publishes.

Version pinning stays in force for everything else the roles fetch — the
directly downloaded binaries in `dev_tools`, and the installer- and
registry-sourced tools pinned in each role's `defaults/` and kept current by
Renovate's regex managers (`ansible/AGENTS.md`).

The consequence is accepted: two builds of the same commit can ship different
apt package versions, and a regression caused by an upstream package update
cannot be bisected to a change in this repository.

## Alternatives considered

**Pinning every apt package per Ubuntu release and architecture**, in a
generated `roles/<role>/vars/apt_pins_<suite>_<arch>.yml` per role, refreshed by
a script and kept current by Renovate `deb` custom managers batched into one
daily automerged pull request. Rejected for its costs:

- **Pins rot.** Ubuntu drops a version from `-updates` and `-security` as soon
  as it is superseded, so a pin becomes unfetchable the moment upstream
  republishes and the image build fails until the next batch merges.
- **Every batch rebuilds the image.** The pin files live under `ansible/`,
  inside the CI image path filter, so each merged batch is a multi-arch rebuild.
  The schedule trades the breakage window against rebuild count; neither goes
  away.
- **Two unguarded copies of each role's repository set.** A pin is installable
  only from a repository the role enables, so the refresh script and Renovate's
  per-role `registryUrls` each had to list the same repositories, with nothing
  enforcing that they agree.
- **Release- and architecture-specific roles.** A consumer on another Ubuntu
  release or architecture fails on the missing pin file until it adds one.
- **Partial reproducibility.** Only the named packages are pinned; their
  dependency closures still resolve to whatever apt picks.
