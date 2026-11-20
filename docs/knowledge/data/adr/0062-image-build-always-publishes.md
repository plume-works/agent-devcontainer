---
type: adr
stage: accepted
description: The CI image build always pushes its images, so a pull request from a fork fails at the push and a maintainer runs it from a branch of this repository.
---

# The CI image build always publishes

The image build is the first stage of CI. The Dev Container acceptance jobs, and
the suites of each consumer, run in the images that it pushed. For this reason,
the build pushes each image with no condition on the head repository. A fork run
that published nothing would pass having proved only that the Dockerfiles
compile, so a pull request from a fork fails at the push instead.

## Considered Options

- Make the push and the later jobs depend on a publish result. Rejected: each
  later stage, here and in each consumer, needs its own condition. That makes a
  second CI structure next to the one that publishes. Also, each image builds
  from the digest of the image that the same run pushed before it. A run with no
  push builds on the last published image, so a change to a lower image does not
  go into the images above it. The acceptance jobs pull the candidate image from
  the registry, so with no push they have no image to test.
- A personal access token or `pull_request_target` for fork builds. Rejected:
  unreviewed code would then reach the registry. The read-only token of a fork
  stays the boundary.

## Consequences

- A maintainer runs an external contribution from a branch of this repository.
