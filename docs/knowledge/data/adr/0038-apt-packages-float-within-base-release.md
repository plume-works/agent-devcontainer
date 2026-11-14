---
type: adr
stage: accepted
description: The Ansible roles install apt packages by name with no version, and the fixed Ubuntu 24.04 base limits what an apt update can change.
---

# apt packages have no fixed version within a fixed Ubuntu release

The roles pin each downloaded binary and each tool from an installer or a
registry. They install apt packages by name with no version. The base image
fixes the Ubuntu release, and apt keeps the packages of one release compatible.
Renovate does not change the Ubuntu release. A different release ships as an
image tag with a different name.

## Considered Options

- Pin each apt package for each Ubuntu release and architecture, in generated
  pin files that Renovate `deb` managers update. Rejected: Ubuntu removes an old
  version from `-updates` and `-security`, so a pin fails the build until the
  next update merges. Each update rebuilds all architectures. Each repository
  set is in two places with nothing to keep them the same. The dependencies of
  pinned packages still have no fixed version.

## Consequences

- Two builds of one commit can ship different apt versions.
- A regression from an upstream package update has no commit in this repository
  to bisect to.
