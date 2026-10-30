---
type: spec
description: How the published ubuntu-ansible, agentdev-base, agentdev-deploy, and agentdev-devcontainer images are tagged after acceptance, and pinned and updated by consumers.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T02:01:26Z
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

### Scenario: Renovate bumps the Dev Container digest

- **WHEN** Renovate proposes a new `agentdev-devcontainer` digest
- **THEN** one pull request changes the Compose pin and every workflow
  `container.image` reference to that digest.

### Scenario: a bumped digest is exercised before merge

- **WHEN** a pull request changes the Dev Container digest
- **THEN** a required check runs inside it and the pull request cannot merge
  while that check fails.

## Requirement: published tags name only tested images

CI SHALL publish `ubuntu-ansible`, `agentdev-base`, `agentdev-deploy`, and
`agentdev-devcontainer` candidates under immutable commit tags and SHALL move
event tags only after native deploy and Dev Container acceptance pass for the
same digests, without rebuilding. CI SHALL NOT move a tag to an image built from
an ancestor of the commit it names. Primary checks runs on `main` SHALL NOT
cancel one another.

### Scenario: every acceptance check passes

- **WHEN** the run's image and runtime checks pass
- **THEN** the event's moving tags name the exact digests that run built and
  tested.

### Scenario: a check fails or the run is cancelled

- **WHEN** any required acceptance job fails or the run is cancelled
- **THEN** every moving tag keeps its previous digest, and only the immutable
  commit tag names the new image family.

### Scenario: an older run is re-run

- **WHEN** an older commit passes after a newer commit was promoted
- **THEN** moving tags keep the newer image family.

### Scenario: pushes to main arrive during a run

- **WHEN** commits land on `main` while its run is in progress
- **THEN** that run completes, and the newest waiting run follows it.

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

## Unknowns

- The exact policy for how often the digest pin should be advanced (on every
  Renovate PR vs. batched) is not written down anywhere found in the code.
