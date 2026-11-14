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

## Rationale

### The browser comes from Playwright's installer at the pinned version

Playwright's browser binaries are coupled to its client release, so the image
installs Chromium with the pinned Playwright CLI itself.

Rejected:

- **Ubuntu's Chromium package.** A distribution package does not keep
  Playwright's client and browser versions matched.

### The browser is its own opt-in role

`playwright_browser` is an Ansible role of its own, enabled by
`install_playwright_browser` and run after the Bun and Node roles, because the
browser binaries and their OS dependencies are an image capability selected
independently of the agent CLIs.

Rejected:

- **A task inside `agentic_tools`.** It would tie the browser to the agent CLIs.

### The image ships a browser, not a browsing toolkit

The capability is a launchable browser: the image bundles the Playwright CLI and
Chromium only, and leaves everything built on them to the projects that use
them.

Rejected:

- **Bundling Firefox or WebKit.** Outside the capability, which is one
  version-matched browser.
- **A Playwright MCP server, agent skill, test framework, or project-level
  Playwright configuration.** Outside the capability; a project that wants one
  adds it.
- **Relaxing the opt-in egress firewall for browsing.** The firewall keeps its
  own policy.
