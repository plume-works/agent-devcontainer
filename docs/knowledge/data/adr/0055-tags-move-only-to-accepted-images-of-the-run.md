---
type: adr
stage: accepted
description: Each CI run builds, tests, and then promotes its own candidate images, and a moving tag moves only after acceptance and never to an older commit.
---

# A run promotes only the images it built and accepted

A CI run builds candidate images, runs acceptance on them, and then promotes
them. A squash merge or a Renovate commit gives `main` a tree that no pull
request tested. A rebuild is also different, because apt packages and upstream
repositories change between builds. As a result, a moving tag names only an
image that passed acceptance in the same run.

## Considered Options

- Promote the image that a pull request tested when it merges. Rejected: the
  merged tree is not the tree that the pull request tested.
- Publish on `main` and test the published tags after that. Rejected: a failed
  image is then public, and an older run can overwrite the tags of a newer run.
- Cancel a run on `main` after its build starts. Rejected: when merges occur
  continuously, `edge` never moves.

## Consequences

- Runs on `main` do not end in order. `.github/actions/docker/promote` does not
  move a tag that names a newer commit.
