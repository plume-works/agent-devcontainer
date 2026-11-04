---
type: architecture
description: The image installs no package from a Launchpad PPA; the latest git is built from its kernel.org source release, and every other tool newer than Ubuntu ships comes from its vendor's signed apt repository or a pinned, checksum-verified release archive.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-04T17:05:00Z
sources:
- resource: ansible/roles/git_source/tasks/main.yml
- resource: ansible/roles/git_source/defaults/main.yml
- resource: ansible/roles/dev_tools/tasks/main.yml
- resource: .devcontainer/firewall-allowlist.txt
- resource: scripts/refresh-pin-checksums.py
---

# No Launchpad PPAs

The Ansible roles that provision the image add no Launchpad PPA, and the
devcontainer firewall allows neither `launchpad.net` nor
`ppa.launchpadcontent.net`.

A package comes from one of four sources, in this order of preference:

1. The Ubuntu archive (`archive.ubuntu.com`, `ports.ubuntu.com`).
2. The vendor's own apt repository, with its signing key installed under a
   `signed-by` keyring, as the `github_cli`, `install_docker`, `cmake_kitware`
   and `xpra_setup` roles do.
3. A pinned release archive with a SHA-256 checksum per architecture, through
   `dev_tools_pinned_tools`.
4. A pinned source release built in the image, when the vendor publishes neither
   an apt repository nor a binary for Linux.

## git

The image carries the latest upstream git. Upstream publishes no apt repository
and no Linux binary, so the `git_source` role builds the release tarball from
`cdn.kernel.org`, verified against its pinned SHA-256, into `/usr/local`.
Renovate bumps `git_source_version` from the `git/git` release tags, and
`scripts/refresh-pin-checksums.py` rehashes the tarball in the same commit. The
build uses Ubuntu's `cargo`, so git's Rust components are built as in upstream's
default build; they need no crate from crates.io.

Ubuntu's `git` package stays installed, because `gh`, `docker-ce` and `git-lfs`
depend on it. `/usr/local/bin` precedes `/usr/bin` on `PATH`, and the role fails
the build when `git` on `PATH` is not the pinned build.

## Why

- The `ppa:` shorthand of `ansible.builtin.apt_repository` fetches the signing
  key from the Launchpad API at build time, so an outage of that API fails the
  image build on every architecture.
- A PPA is published by a third party rather than by the tool's vendor, and adds
  a host to the firewall allowlist of every container.

## Rejected alternatives

- **Keep the Git Core PPA with a pinned key and an explicit `deb` entry.** It
  removes the Launchpad API call but still depends on Launchpad's archive host.
- **Ubuntu's own git.** It trails the upstream release by the age of the base
  image's Ubuntu release.
- **Replace Ubuntu's `git` package with a dummy package built with `equivs`.**
  It hides the source-built git from dpkg so that no second copy exists, at the
  cost of a hand-made package that lies about what is installed.
