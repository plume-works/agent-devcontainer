---
type: spec
description: How the published ubuntu-ansible, agentdev-base, agentdev-deploy, and agentdev-devcontainer images are tagged after acceptance, and pinned and updated by consumers.
sources:
- resource: devcontainer-compose-pins.yml
- resource: README.md
- resource: .github/renovate.json
- resource: .github/workflows/validate-renovate-config.yml
- resource: .github/workflows/ci.yml
- resource: .github/workflows/primary-checks.yml
- resource: .github/actions/docker/promote/action.yml
- resource: .github/actions/docker/multiarch-merge/action.yml
- resource: opencode-compose-pins.yml
- resource: .github/actions/paths-filter/action.yml
- resource: docker/ansible/Dockerfile
- resource: scripts/ci-cooldown.py
---

# Image pinning

## Requirement: published tags name only tested images

CI SHALL publish `ubuntu-ansible`, `agentdev-base`, `agentdev-deploy`, and
`agentdev-devcontainer` candidates under immutable commit tags and SHALL move
event tags only after native deploy and Dev Container acceptance and the
candidate pre-commit run pass for the same digests, without rebuilding. CI SHALL
NOT move a tag to an image built from an ancestor of the commit it names, which
it reads from the `org.opencontainers.image.revision` label of the image the tag
names; a label naming a commit outside the checkout's history SHALL NOT block
the move. No Primary checks run SHALL cancel a run on `main` whose `ci` job has
started, while a newer run on any other ref SHALL cancel the older run for that
ref.

### Scenario: every acceptance check passes

- **WHEN** the run's image and runtime checks pass
- **THEN** the event's moving tags name the exact digests that run built and
  tested.

### Scenario: a check fails or the run is cancelled

- **WHEN** any required acceptance job fails or the run is cancelled
- **THEN** every moving tag keeps its previous digest, and only the immutable
  commit tag names the new image family.

### Scenario: a moving tag names a commit outside the history

- **WHEN** a moving tag's image carries a revision label naming a commit the
  checkout does not hold, such as a pull request's earlier merge commit
- **THEN** the run moves the tag to its own tested digest.

### Scenario: pushes to main arrive during a run

- **WHEN** commits land on `main` after a run's `ci` job started and before that
  run completes
- **THEN** that run completes, and the newest waiting run follows it.

## Unknowns

- The exact policy for how often the digest pin should be advanced (on every
  Renovate PR vs. batched) is not written down anywhere found in the code.

## Rationale

### Each run promotes the images it built and tested

A run builds, tests, and then promotes its own images, because squash merges and
Renovate commits make `main`'s tree differ from any tested pull request head.
Runs on `main` queue instead of cancelling, so `edge` keeps advancing while
merges, Renovate automerges among them, arrive faster than one run completes.

Rejected:

- **Promoting the image a pull request tested when it merges.** The merged tree
  is not the tree that pull request tested.
- **Cancelling an in-progress run on `main`.** A steady stream of merges would
  keep `edge` from ever moving.

### Pushes to main build after a cancellable cooldown

Every Primary checks run on `main` is a clean multi-arch build, and runs on
`main` queue rather than cancel once building, so back-to-back merges would each
build in turn. A cooldown job in its own cancel-in-progress group lets a newer
push cancel a run that has not started building, so a burst of merges builds
once. The cap keeps a steady stream of merges from postponing every build. The
workflow-level group is per run on `main` so a run queued for the `ci` job never
blocks the next run's cooldown.

Rejected:

- **A merge queue.** It builds every queued pull request's `merge_group` ref and
  then the push to `main` again, multiplying builds instead of saving them.
- **A deployment environment wait timer.** It spends no runner time, but GitHub
  does not document whether concurrency cancels a job waiting on one.

### Tags move only after acceptance

A moving tag names only an image that passed acceptance, because neither
assumption behind publishing first and testing after holds. A rebuild on `main`
is not equivalent to the image a pull request tested: unpinned apt packages and
upstream repositories change between builds. Runs on `main` do not finish in
order, so the last run to publish need not be the newest commit.

Rejected:

- **Publish on `main`, then test the published tags.** A failing image is
  already published, and an older run can overwrite a newer one's tags.

### The weekly Ubuntu digest bump is the scheduled clean rebuild

Renovate's weekly bump of the `ubuntu:24.04` digest changes the root of every
image, so it is the scheduled rebuild from a fresh base; between bumps `main`
and pull requests share the layer cache.

Rejected:

- **Warm-starting builds from the published `agentdev-base:edge`.** The shared
  layer cache already reuses unchanged steps, and the weekly bump already
  refreshes the base.

### Digest copies agree through one Renovate group

Every copy of the development image digest moves in one change because a
Renovate group rule in `.github/renovate.json` updates them together.

Rejected:

- **A check that every copy of the digest agrees.** The group rule already moves
  them together, and a hand edit that splits them is reviewed like any other
  change.
