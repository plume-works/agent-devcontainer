---
type: adr
stage: accepted
description: The CI image build always pushes its images, so a pull request from a fork fails at the push and a maintainer runs it from a branch of this repository.
---

# The CI image build always publishes

The image build is the first stage of CI. The Dev Container acceptance jobs, and
the suites of each consumer, run in the images that it pushed. For this reason,
the build pushes each image with no condition on the head repository. A pull
request from a fork fails at the push.

## Considered Options

- Make the push and the later jobs depend on a publish result. Rejected: each
  later stage, here and in each consumer, needs its own condition. That makes a
  second CI structure next to the one that publishes. Also, each image builds
  from the digest of the image that the same run pushed before it. A run with no
  push builds on the last published image, so a change to a lower image does not
  get into the images above it. The acceptance jobs pull the candidate image
  from the registry, so with no push they have no image to test.
- A personal access token or `pull_request_target` for fork builds. Rejected:
  code that nobody reviewed could write to the registry.

## Consequences

- A maintainer runs an external contribution from a branch of this repository.
- Support for fork builds becomes useful only when a later stage can use an
  image of the run without a registry write, also for consumers. A local
  registry service on the runner, or an image store that all stages use, can
  give this.
- An optional push is correct for a repository whose image build is the last
  stage, because no later stage uses its image.
