---
type: adr
stage: accepted
---

# apt packages float within a fixed Ubuntu release

The roles pin each downloaded binary and each tool from an installer or a
registry. They install apt packages by name, unpinned, and apt installs whatever
the repositories that the role enables serve at build time. The base image ties
each image to one Ubuntu release, and within one release apt keeps its own
packages mutually compatible, so a fixed base already bounds what an unpinned
install can change. The base stays at Ubuntu 24.04 because consumers depend on
it, and Renovate does not bump it. Another release ships as a separately named
image tag with an explicit base.

## Considered Options

- Pin each apt package for each Ubuntu release and architecture, in generated
  pin files that Renovate `deb` managers update. Rejected: Ubuntu drops a
  version from `-updates` and `-security` as soon as it is superseded, so a pin
  becomes unfetchable and the image build fails until the next update merges.
  The pin files are inside the CI image path filter, so each merged update is a
  multi-arch rebuild. A pin installs only from a repository that the role
  enables, so the refresh script and Renovate's per-role `registryUrls` both
  list the same repositories, with nothing to make them agree. A consumer on a
  different Ubuntu release or architecture fails until it adds its own pin file.
  Only the named packages are pinned; their dependency closures still resolve to
  whatever apt picks.

## Consequences

- Two builds of one commit can ship different apt package versions.
- A regression caused by an upstream package update cannot be bisected to a
  change in this repository.
