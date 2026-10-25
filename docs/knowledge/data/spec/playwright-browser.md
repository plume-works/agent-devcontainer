---
type: spec
description: The pinned Playwright CLI and matching Chromium browser the published agent-desktop image provides, and the boundary with project-owned Playwright dependencies.
generated:
  by: claude-code/opus-5
  at: 2026-10-25T06:36:50Z
sources:
- resource: ansible/roles/playwright_browser/defaults/main.yml
- resource: ansible/roles/playwright_browser/tasks/main.yml
- resource: ansible/playbooks/setup-dev.yml
- resource: docker/desktop/agent-desktop.Dockerfile
- resource: .github/workflows/ci.yml
- resource: https://playwright.dev/docs/browsers
---

# Playwright browser

## Requirements

### Requirement: the development image provides a version-matched Playwright browser

The published `agent-desktop` image SHALL provide a pinned Playwright CLI and
its matching Chromium browser and Linux dependencies from an image-owned path.

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

### Requirement: project Playwright dependencies remain project-owned

The bundled browser capability SHALL NOT claim compatibility with a consumer
project's independently versioned Playwright dependency.

#### Scenario: a project uses a different Playwright release

- **WHEN** a consumer project requires browser binaries for a Playwright release
  other than the image pin
- **THEN** the project installs and uses the browser binaries matched to its own
  dependency.
