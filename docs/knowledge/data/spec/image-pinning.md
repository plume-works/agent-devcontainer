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

## Requirement: images are pinned by tag and digest, never a bare moving tag

The canonical `agentdev-devcontainer` and `agentdev-deploy` consumer
configurations SHALL reference their image by tag and digest so an upstream
rebuild never silently changes a running environment.

### Scenario: a canonical image is rebuilt with the same tag

- **WHEN** either canonical moving tag is rebuilt and pushed again
- **THEN** a consumer's pinned digest still resolves to the old image until the
  pinned digest is updated.

## Requirement: `devcontainer-compose-pins.yml` stays outside the image-build path filter

`devcontainer-compose-pins.yml` SHALL live at the repository root, outside
`.devcontainer/` and `docker/`, so that a digest-only bump does not match the
`image` path filter in `.github/actions/paths-filter/action.yml`.

### Scenario: Renovate bumps the digest pin

- **WHEN** Renovate opens a PR that only changes the digest in
  `devcontainer-compose-pins.yml`
- **THEN** the change does not retrigger the image build/publish job, because
  that build is not bit-reproducible and a self-triggering loop would bump the
  pin forever.

## Requirement: `.devcontainer/docker-compose.yml` carries tag only

`.devcontainer/docker-compose.yml` SHALL reference the image by tag only;
`devcontainer-compose-pins.yml` overrides it with the digest-qualified reference
via `dockerComposeFile` in `devcontainer.json`.

## Requirement: workflow container images share the devcontainer pin

Every workflow job that runs in the development runtime SHALL reference the same
`agentdev-devcontainer` tag and digest as `devcontainer-compose-pins.yml`, and a
digest update SHALL move every reference in one change.

### Scenario: a bumped digest is exercised before merge

- **WHEN** a pull request changes the Dev Container digest
- **THEN** a required check runs inside it and the pull request cannot merge
  while that check fails.

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

## Requirement: pushes to main build after a cooldown

A Primary checks run started by a push to `main` SHALL wait
`MAIN_COOLDOWN_SECONDS` (default 600) before any build job starts, and a newer
push to `main` SHALL cancel a run that is still waiting. The wait SHALL end no
later than `MAIN_COOLDOWN_MAX_SECONDS` (default 1800) after the start of the
oldest push run since the newest push run that was not cancelled. Pull requests,
merge groups, tags, and `workflow_dispatch` SHALL NOT wait. When the run history
cannot be read, the run SHALL wait the full cooldown. The waiting job holds a
runner for the whole wait.

### Scenario: pushes keep arriving past the cap

- **WHEN** pushes keep landing on `main` until the oldest waiting push is older
  than the cap
- **THEN** the newest run starts building at the cap, and the next push waits a
  full cooldown.

### Scenario: the cooldown is turned off

- **WHEN** `MAIN_COOLDOWN_SECONDS` is `0`
- **THEN** a push to `main` starts building at once.

## Requirement: standalone runtime deployment is digest-pinned

Supported `agentdev-deploy` Compose launch commands SHALL include a
tag-and-digest pin in root-level `opencode-compose-pins.yml`. Runtime builds
SHALL use the exact `agentdev-base` digest from their build run. A pin change
SHALL NOT rebuild or publish the image it names.

### Scenario: runtime sources change

- **WHEN** a runtime image is built and published
- **THEN** native amd64 and arm64 builds and acceptance checks gate success and
  the manifest identifies the corresponding `agentdev-base` ancestry.

### Scenario: only a deployment digest changes

- **WHEN** Renovate advances `opencode-compose-pins.yml`
- **THEN** the proposed digest is one CI promoted after acceptance, the
  image-build path filter does not match, and the update does not create a
  publish/pin loop.

## Requirement: the Ubuntu base is pinned by digest and refreshed weekly

The `ubuntu-ansible` build SHALL start from `ubuntu:24.04` pinned by digest in
`docker/ansible/Dockerfile`'s `BASE_IMAGE` default, and CI SHALL NOT override
it. Renovate SHALL update only that digest, on a weekly schedule, and SHALL
automerge the update once required checks pass; the release SHALL NOT move off
24.04.

### Scenario: a new 24.04 digest is published

- **WHEN** Renovate's weekly run finds a newer `ubuntu:24.04` digest
- **THEN** it opens one pull request that changes only the digest, the run
  rebuilds and accepts the images from the new base, and the pull request
  automerges when its checks pass

### Scenario: a pull request builds the images

- **WHEN** a pull request's run builds `ubuntu-ansible`
- **THEN** it starts from the pinned digest, never from a published
  `agentdev-base` image

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
