---
type: adr
stage: accepted
---

# A run promotes only the images it built and accepted

A CI run builds candidate images, runs acceptance on them, and then promotes
them. A squash merge or a Renovate commit gives `main` a tree that differs from
any tested pull request head. A rebuild on `main` is not equivalent to the image
a pull request tested either, because unpinned apt packages and upstream
repositories change between builds. As a result, a moving tag names only an
image that passed acceptance in the same run. Runs on `main` queue instead of
cancelling, so `edge` keeps advancing while merges, Renovate automerges among
them, arrive faster than one run completes.

## Considered Options

- Promote the image that a pull request tested when it merges. Rejected: the
  merged tree is not the tree that the pull request tested.
- Publish on `main` and test the published tags after that. Rejected: a failed
  image is then public, and an older run can overwrite the tags of a newer run.
- Cancel a run on `main` after its build starts. Rejected: a steady stream of
  merges would keep `edge` from ever moving.

## Consequences

- Runs on `main` do not finish in order, so the last run to publish need not be
  the newest commit. `.github/actions/docker/promote` does not move a tag that
  names a newer commit.
