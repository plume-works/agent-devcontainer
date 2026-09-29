---
type: spec
description: How the published agent-desktop and ubuntu-ansible images are pinned and updated by consumers.
generated:
  by: claude-code/opus-5.5
  at: 2026-09-29T20:00:00Z
sources:
- resource: devcontainer-compose-pins.yml
- resource: README.md
- resource: .github/renovate.json
- resource: .github/workflows/validate-renovate-config.yml
---

# Image pinning

## Requirement: images are pinned by tag and digest, never a bare moving tag

The devcontainer SHALL reference `ghcr.io/plume-works/agent-desktop` by tag and
digest (`:edge@sha256:...` for consumers; this repository pins to a PR-scoped
tag in `devcontainer-compose-pins.yml` while iterating) so that a rebuild
upstream never silently changes what a running container uses.

### Scenario: upstream image is rebuilt with the same tag

- **WHEN** `ghcr.io/plume-works/agent-desktop:edge` is rebuilt and pushed again
- **THEN** a consumer's pinned digest still resolves to the old image until the
  pin is deliberately advanced.

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

Every workflow job that runs in `ghcr.io/plume-works/agent-desktop` SHALL
reference it by the same tag and digest as `devcontainer-compose-pins.yml`, and
a digest update SHALL move every reference in one change.

### Scenario: Renovate bumps the agent-desktop digest

- **WHEN** Renovate proposes a new agent-desktop digest
- **THEN** one pull request changes `devcontainer-compose-pins.yml` and every
  workflow `container.image` to that digest.

### Scenario: a bumped digest is exercised before merge

- **WHEN** a pull request changes the agent-desktop digest
- **THEN** a required check runs inside the new image, and the pull request
  cannot merge while it fails.

## Unknowns

- The exact policy for how often the digest pin should be advanced (on every
  Renovate PR vs. batched) is not written down anywhere found in the code.
