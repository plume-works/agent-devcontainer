---
type: architecture
description: Building the image contacts no Launchpad host; the Git Core PPA's git builds come from unchanged copies in plume-works/git-releases, which a daily workflow publishes after verifying the PPA's signed index.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-04T19:10:00Z
sources:
- resource: ansible/roles/git_ppa/tasks/main.yml
- resource: ansible/roles/git_ppa/defaults/main.yml
- resource: .devcontainer/firewall-allowlist.txt
- resource: scripts/refresh-pin-checksums.py
- resource: https://github.com/plume-works/git-releases
---

# No Launchpad PPAs

Building the image contacts no Launchpad host: no Ansible role adds a PPA, and
the devcontainer firewall allows neither `launchpad.net` nor
`ppa.launchpadcontent.net`.

A package comes from one of four sources, in this order of preference:

1. The Ubuntu archive (`archive.ubuntu.com`, `ports.ubuntu.com`).
2. The vendor's own apt repository, with its signing key installed under a
   `signed-by` keyring, as the `github_cli`, `install_docker`, `cmake_kitware`
   and `xpra_setup` roles do.
3. A pinned release archive with a SHA-256 checksum per architecture, through
   `dev_tools_pinned_tools`.
4. A PPA's packages republished unchanged as GitHub releases in a `plume-works`
   repository, pinned by tag and SHA-256.

## git

The image carries the Git Core PPA's build of the latest upstream git. The
[plume-works/git-releases](https://github.com/plume-works/git-releases)
repository republishes each of the PPA's noble builds as a release holding the
`git` packages for amd64 and arm64 and the matching `git-man` package. Its daily
workflow accepts the PPA's `InRelease` only with a valid signature by the pinned
PPA key `F911AB184317630C59970973E363C90F8F1B6217`, and checks each `Packages`
index and `.deb` against the SHA-256 the signed index chains to. The release
notes record each file's PPA URL and SHA-256.

The `git_ppa` role downloads the pinned release's packages, checks their
SHA-256, and installs `git` and `git-man` in one apt transaction, replacing
Ubuntu's `git`, or a newer build an image it starts from already carries. It
also deletes the `git-core-ppa` apt source, so an image or host provisioned
while git came straight from the PPA stops contacting Launchpad. Renovate bumps
`git_ppa_version` from the repository's releases, and
`scripts/refresh-pin-checksums.py` rehashes both packages in the same commit.

The PPA keeps only its newest build. A release is therefore the only lasting
copy of a build, and the workflow never replaces one that exists. GitHub
disables a public repository's scheduled workflows after 60 days without
activity; while disabled, new PPA builds are missed.

## Why

- The `ppa:` shorthand of `ansible.builtin.apt_repository` fetches the signing
  key from the Launchpad API at build time, so an outage of that API fails the
  image build on every architecture.
- An apt source on `ppa.launchpadcontent.net` makes every image build depend on
  Launchpad's archive host.

## Rejected alternatives

- **An apt source on `ppa.launchpadcontent.net` with a pinned key.** It removes
  the Launchpad API call but keeps the build's dependency on Launchpad.
- **Pinned URLs into the PPA's pool.** The PPA deletes a build once a newer one
  is published, so every pin breaks at the PPA's next upload.
- **Ubuntu's own git.** It trails the upstream release by the age of the base
  image's Ubuntu release.
- **Building git from its kernel.org source release in the image.** It adds a
  compile of over a minute per architecture and a Rust toolchain to every image
  build.
