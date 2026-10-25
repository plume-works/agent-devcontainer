---
type: feature
stage: implemented
description: The published development image includes a version-matched Playwright CLI and Chromium browser for agent-driven web automation.
generated:
  by: codex/gpt-5
  at: 2026-10-21T07:02:02Z
sources:
- resource: https://playwright.dev/docs/browsers
- resource: https://playwright.dev/docs/docker
- resource: ansible/playbooks/setup-dev.yml
- resource: docker/desktop/agent-desktop.Dockerfile
---

# Playwright browser in the development image

## Purpose

Give agents and developers a browser that works immediately in the published
development image, without a runtime browser download or project-specific
bootstrap step.

## Behaviour

The image provides a pinned Playwright CLI and the matching Chromium browser
with its Linux dependencies on both published architectures. The installation is
available to raw-image and devcontainer consumers and supports headless launches
from the command line.

Consumer projects remain responsible for browser binaries required by their own
Playwright dependency when its version differs from the image pin.

## Edge cases

- The browser installation must not live under a home-directory cache that a
  devcontainer volume can hide.
- The image's optional egress firewall continues to govern destinations the
  browser may reach.
- A Playwright version update must update the CLI and bundled browser together.

## Open questions

None.
