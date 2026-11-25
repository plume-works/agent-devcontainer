---
type: adr
stage: superseded
---

# Image builds get no package from Launchpad

The `ppa:` shorthand gets the signing key from the Launchpad API at build time.
As a result, a failure of that API stops the image build on each architecture. A
PPA apt source makes each build depend on the archive host of Launchpad. For
this reason, a package comes from one of these sources, in this order of
preference:

1. The Ubuntu archive.
2. The apt repository of the vendor, with a `signed-by` key.
3. A pinned release archive, with a SHA-256 for each architecture, through
   `dev_tools_pinned_tools`.
4. A release `pinned-deps/<name>/<version>` of this repository, which
   republishes the packages of a PPA unchanged, pinned by tag and SHA-256.

The image uses the git of the Git Core PPA, because the git of Ubuntu is older
than the upstream release.

## Considered Options

- A PPA apt source with a pinned key. Rejected: the build still depends on
  Launchpad.
- Releases in a dedicated repository. Rejected: GitHub disables the scheduled
  workflows of a public repository after 60 days without activity, which a
  repository that holds only releases reaches. Also, a publish from this
  repository needs a cross-repository credential.
- Pinned URLs into the pool of the PPA. Rejected: the PPA deletes a build when
  it publishes a newer build, so each pin breaks at the next upload.
- Build git from its kernel.org source release in the image. Rejected: each
  build then compiles for more than one minute for each architecture and needs a
  Rust toolchain.

## Consequences

- The PPA keeps only its newest build, so the release is the only permanent
  copy. `scripts/cache-git-ppa-release.py` never replaces a release, and it
  never marks a release as the latest release of the repository.
