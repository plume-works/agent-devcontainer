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

### Requirement: project Playwright dependencies remain project-owned

The bundled browser capability SHALL NOT claim compatibility with a consumer
project's independently versioned Playwright dependency.

#### Scenario: a project uses a different Playwright release

- **WHEN** a consumer project requires browser binaries for a Playwright release
  other than the image pin
- **THEN** the project installs and uses the browser binaries matched to its own
  dependency.
