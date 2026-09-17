---
type: architecture
description: Why the image build is not made fork-compatible by publishing nothing — it is the first stage of CI, not a leaf, and every stage after it consumes the image it published.
generated:
  by: claude-code/opus-5
  at: 2026-09-17T00:00:00Z
sources:
- resource: .github/workflows/ci.yml
- resource: https://github.com/plume-works/coder-ide-baseline/pull/3
---

# Fork pull request builds

## Decision

A pull request from a fork **is not made to pass** by building the images
without publishing them. `ci.yml` pushes unconditionally; a fork run fails at
that push, and that is accepted.

## Why publishing is not optional here

The image build is the **first** stage of CI, not a leaf. Everything after it
consumes what it published: in this repository the devcontainer smoke test, and
in a consumer that inherits the workflow —
[Dr-QP/Dr.QP](https://github.com/Dr-QP/Dr.QP) — the application's own suites,
which run inside that image.

So a build that publishes nothing hands every later stage nothing to pull. The
fork run would go green having proved that two Dockerfiles compile, while the
work the pipeline exists to do never ran. Making that honest means gating the
whole downstream pipeline on the same verdict, here and in every consumer.

## Rejected: gate the pushes and everything downstream on a publish verdict

The shape considered: one `publish` verdict, false when the head repository
differs from the base, gating the registry writes — the per-architecture pushes
and the manifest merge — plus the digest artifacts they feed and the digest-pin
patch in the devcontainer smoke test; `docker/build-push-action` gaining a
`push` input; jobs downstream of the now-skippable merge carrying explicit
`always()` conditions.

It fails on what the surviving green check would mean:

- The desktop image is built `FROM` the base the same run pushed. A fork run
  cannot push it, so the desktop image would build on the last **published**
  base — a change under `docker/ansible/` gets built and never composed.
- The devcontainer smoke test would run against the committed digest pin, which
  is an image the pull request did not produce.
- Every stage after the build, in this repository and in each consumer, needs
  its own skip. The gate is not a change to the build; it is a second CI
  topology maintained beside the one that publishes.

The pattern fits a repository whose image build **is** a leaf — the published
image is the product and nothing downstream consumes it in the same run.
`plume-works/coder-ide-baseline` is that shape and keeps it.

## What would have to change first

Fork builds become worth supporting when a later stage can consume an image the
run itself produced without a registry write — a runner-local registry service
or a shared image store the whole pipeline resolves through. That condition has
to hold for consumers too, since they inherit the workflow along with the
constraint.

## Consequences

- An external contribution is reviewed on a branch in this repository rather
  than from the fork; a maintainer pushes the branch to run CI on it.
- The read-only fork token stays the boundary: no PAT and no
  `pull_request_target` reaches the registry from unreviewed code.

## Status

Rejected 2026-09-16, before implementation.
