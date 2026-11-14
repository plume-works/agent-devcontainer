---
type: adr
stage: accepted
description: Image builds get no package from a Launchpad host; the git build of the Git Core PPA comes from a release of this repository.
---

# Image builds get no package from Launchpad

The `ppa:` shorthand gets the signing key from the Launchpad API at build time,
so a failure of that API stops the image build on each architecture. A PPA apt
source makes each build depend on the archive host of Launchpad. For this
reason, a package comes from one of these sources, in this order of preference:

1. The Ubuntu archive.
2. The apt repository of the vendor, with a `signed-by` key.
3. A pinned release archive, with a SHA-256 for each architecture.
4. A release `pinned-deps/<name>/<version>` of this repository, which holds the
   packages of a PPA without change.

The image uses the git of the Git Core PPA, because the git of Ubuntu is older
than the upstream release.

## Considered Options

- A PPA apt source with a pinned key. Rejected: the build still depends on
  Launchpad.
- Releases in a separate repository. Rejected: GitHub stops the scheduled
  workflows of a public repository after 60 days without activity. Also, a
  publish from this repository needs a credential for the other repository.
- Pinned URLs into the pool of the PPA. Rejected: the PPA deletes a build when
  it publishes a newer build, so each pin breaks.
- The git of Ubuntu. Rejected: it is older than the upstream release by the age
  of the Ubuntu release of the base image.
- Build git from its source release in the image. Rejected: each build then
  compiles for more than one minute for each architecture and needs a Rust
  toolchain.

## Consequences

- The PPA keeps only its newest build, so the release is the only permanent
  copy. `scripts/cache-git-ppa-release.py` never replaces a release, and it
  never marks a release as the latest release of the repository.
- The script accepts the `InRelease` index of the PPA only with a valid
  signature of the pinned key in `scripts/git-core-ppa.asc`. It checks each
  `Packages` index and each `.deb` file against the SHA-256 that the signed
  index gives.
- The `git_ppa` role installs `git` and `git-man` in one apt transaction,
  because `git` needs `git-man` at the same version. The role also removes the
  `git-core-ppa` apt source, so an image or a host that got git from the PPA
  before stops its access to Launchpad.
- Renovate changes `git_ppa_release_tag` to a newer `pinned-deps/git/` release,
  and `scripts/refresh-pin-checksums.py` changes the SHA-256 of both packages in
  the same commit.
