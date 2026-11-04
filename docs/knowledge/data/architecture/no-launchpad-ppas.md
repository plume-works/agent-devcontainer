---
type: architecture
description: The image installs no package from a Launchpad PPA; a tool the Ubuntu archive ships too old comes from its vendor's own signed apt repository or a pinned, checksum-verified release archive.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-04T15:58:06Z
sources:
- resource: ansible/roles/dev_tools/tasks/main.yml
- resource: .devcontainer/firewall-allowlist.txt
---

# No Launchpad PPAs

The Ansible roles that provision the image add no Launchpad PPA, and the
devcontainer firewall allows neither `launchpad.net` nor
`ppa.launchpadcontent.net`. `git` comes from the Ubuntu archive of the base
image's release.

A package comes from one of three sources, in this order of preference:

1. The Ubuntu archive (`archive.ubuntu.com`, `ports.ubuntu.com`).
2. The vendor's own apt repository, with its signing key installed under a
   `signed-by` keyring, as the `github_cli`, `install_docker`, `cmake_kitware`
   and `xpra_setup` roles do.
3. A pinned release archive with a SHA-256 checksum per architecture, through
   `dev_tools_pinned_tools`.

## Why

- The `ppa:` shorthand of `ansible.builtin.apt_repository` fetches the signing
  key from the Launchpad API at build time, so an outage of that API fails the
  image build on every architecture.
- A PPA is published by a third party rather than by the tool's vendor, and adds
  a host to the firewall allowlist of every container.

## Rejected alternatives

- **Keep the Git Core PPA with a pinned key and an explicit `deb` entry.** It
  removes the Launchpad API call but keeps a third-party archive and its host in
  the allowlist. Nothing in the repository needs a `git` newer than the one
  Ubuntu ships.
- **Build `git` from source.** It adds a compiler toolchain run and a version
  pin to maintain for no feature the repository uses.
