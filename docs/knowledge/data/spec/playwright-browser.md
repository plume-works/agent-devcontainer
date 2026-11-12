---
type: spec
description: The pinned Playwright CLI and matching Chromium browser the published agentdev-base image provides to both runtime images, and the boundary with project-owned Playwright dependencies.
sources:
- resource: ansible/roles/playwright_browser/defaults/main.yml
- resource: ansible/roles/playwright_browser/tasks/main.yml
- resource: ansible/playbooks/setup-dev.yml
- resource: docker/base/agentdev-base.Dockerfile
- resource: .github/workflows/ci.yml
- resource: https://playwright.dev/docs/browsers
---

# Playwright browser

## Requirements

### Requirement: the development image provides a version-matched Playwright browser

The published `agentdev-base` image SHALL provide a pinned Playwright CLI and
its matching Chromium browser and Linux dependencies from an image-owned path,
and both runtime images SHALL inherit it. The build SHALL install Chromium with
the pinned CLI itself, from the one version the image is built with, and SHALL
fail when the installed CLI reports another version, so a version update changes
the CLI and the browser together.

#### Scenario: a consumer launches the bundled browser

- **WHEN** a user starts the published image without mounting a home-directory
  browser cache
- **THEN** the Playwright CLI launches the bundled Chromium without downloading
  browser binaries at runtime.

#### Scenario: the image is built for a supported architecture

- **WHEN** CI builds and accepts either the `linux/amd64` or `linux/arm64`
  variant
- **THEN** the same pinned Playwright release and matching Chromium capability
  are present and a headless browser launch succeeds.

#### Scenario: the Playwright pin is updated

- **WHEN** the image is built with a new Playwright version
- **THEN** the image carries that CLI version and the Chromium release it
  matches.

### Requirement: project Playwright dependencies remain project-owned

The bundled browser capability SHALL NOT claim compatibility with a consumer
project's independently versioned Playwright dependency.

#### Scenario: a project uses a different Playwright release

- **WHEN** a consumer project requires browser binaries for a Playwright release
  other than the image pin
- **THEN** the project installs and uses the browser binaries matched to its own
  dependency.
