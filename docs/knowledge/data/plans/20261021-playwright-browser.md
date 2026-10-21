---
type: plan
created: 2026-10-21
release:
- features/playwright-browser
description: Provision and validate a pinned Playwright CLI and matching Chromium browser in the published development image.
generated:
  by: codex/gpt-5
  at: 2026-10-21T07:23:00Z
sources:
- resource: ansible/playbooks/setup-dev.yml
- resource: docker/desktop/agent-desktop.Dockerfile
- resource: .github/workflows/ci.yml
- resource: https://playwright.dev/docs/browsers
- resource: https://playwright.dev/docs/docker
---

# Bundle a Playwright browser in the development image

## Context

[Playwright browser in the development image](../features/playwright-browser.md)
makes browser automation available without downloading a browser after the
container starts. Playwright browser binaries are coupled to the client release,
while this repository publishes the development image for both `linux/amd64` and
`linux/arm64`; the image must therefore install and verify the CLI and Chromium
as one pinned capability on both architectures.

## Approach

Add an opt-in `playwright_browser` Ansible role after Bun and Node provisioning.
The role installs an exact Playwright package with Bun, installs only its
matching Chromium browser and Linux dependencies into an image-owned path, and
exposes the pin to Renovate. Enable the role in `agent-desktop`, publish the
browser path in the image environment, and exercise a real headless launch in
native-architecture image acceptance.

Keep the capability separate from `agentic_tools`: its browser binaries and OS
dependencies form an independently selectable image capability. Reject a bare
Ubuntu Chromium installation because it does not preserve Playwright's
client/browser version contract.

## Implementation Steps

### Task 1: Provision the version-matched browser capability

**Files:** Create: `ansible/roles/playwright_browser/defaults/main.yml`,
`ansible/roles/playwright_browser/tasks/main.yml`,
`ansible/roles/playwright_browser/README.md`; Modify:
`ansible/playbooks/setup-dev.yml`

- [x] Add an opt-in role, ordered after Bun and Node, that installs an exact
  Renovate-managed Playwright package and its matching Chromium plus Linux
  dependencies with Bun-based commands.
  - **Evidence:**
    `uv run ansible-playbook ansible/playbooks/setup-dev.yml --syntax-check` and
    targeted `uv run ansible-lint` passed on 2026-10-21.
- [x] Put browser binaries in `/opt/playwright` and make repeated provisioning
  verify the pinned CLI/browser installation without relying on a user's home
  cache.
  - **Evidence:** The 2026-10-21 targeted Ansible lint run passed with explicit
    CLI-version and installed-browser verification tasks in the role.

### Task 2: Enable Playwright in the published image

**Files:** Modify: `docker/desktop/agent-desktop.Dockerfile`

- [x] Enable the Playwright role for `agent-desktop`, pass its pin explicitly,
  publish `PLAYWRIGHT_BROWSERS_PATH=/opt/playwright`, and label the installed
  Playwright version.
  - **Evidence:**
    `uv run pre-commit run hadolint-docker --files docker/desktop/agent-desktop.Dockerfile`
    passed on 2026-10-21.

### Task 3: Cover provisioning and a real browser launch

**Files:** Create: `scripts/tests/test_playwright_browser_provisioning.py`;
Modify: `.github/workflows/ci.yml`

- [x] Add focused contract tests for the role ordering, opt-in image wiring,
  version pin, image-owned browser path, and Renovate annotation.
  - **Evidence:**
    `uv run pytest scripts/tests/test_playwright_browser_provisioning.py` passed
    all four tests on 2026-10-21; Ruff check also passed.
- [x] Extend devcontainer image acceptance to verify the CLI version and use
  bundled Chromium to load a local or `data:` page headlessly without a runtime
  download.
  - **Evidence:** The focused provisioning suite, Actionlint, and Zizmor passed
    against the CI smoke command on 2026-10-21.

### Task 4: Refresh the affected codebase map

**Files:** Modify: `docs/knowledge/data/codebase/ansible.md`,
`docs/knowledge/data/codebase/flow-image-build.md`, and any other map documents
reported stale for the touched sources

- [ ] Run the IWE map refresh for the implementation changes and validate the
  refreshed graph documents.

### Task 5: Confirm native multi-architecture acceptance

**Files:** None

- [ ] Confirm the image build and browser-launch acceptance pass for both
  `linux/amd64` and `linux/arm64` on the current head.

## Spec changes

`data/spec/playwright-browser`

``` markdown
## ADDED Requirements

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

- **WHEN** a consumer project requires browser binaries for a Playwright
  release other than the image pin
- **THEN** the project installs and uses the browser binaries matched to its own
  dependency.
```

## Verification

- `uv run pytest scripts/tests/test_playwright_browser_provisioning.py`
- Run the repository's Ansible and YAML lint hooks on the new role, playbook,
  Dockerfile, and workflow.
- Build the devcontainer image for both supported architectures and run the CI
  smoke command that launches bundled Chromium against a local or `data:` URL.
- `iwe normalize`
- `iwe schema validate`

## Out of scope

- Bundling Firefox or WebKit.
- Providing browser binaries for arbitrary Playwright versions used by consumer
  projects.
- Relaxing or bypassing the optional devcontainer egress firewall.
- Adding a Playwright MCP server, agent skill, test framework, or project-level
  Playwright configuration.
- Changing shared-memory or sandbox settings unless the native acceptance test
  demonstrates they are required for the supported launch path.

## Key references

Verified anchor points (line numbers as of 2026-10-21):

- `ansible/playbooks/setup-dev.yml:30` — Bun and Node role ordering
- `ansible/playbooks/setup-dev.yml:38` — opt-in image capability roles
- `ansible/roles/agentic_tools/defaults/main.yml:5` — Renovate-managed npm pins
- `ansible/roles/agentic_tools/tasks/main.yml:23` — exact Bun global package
  installation
- `docker/desktop/agent-desktop.Dockerfile:41` — Ansible provisioning layer
- `docker/desktop/agent-desktop.Dockerfile:48` — published-image role inputs
- `.github/workflows/ci.yml:277` — native devcontainer image acceptance
- `.github/workflows/ci.yml:286` — provisioned toolchain smoke checks
- `.devcontainer/docker-compose.yml:53` — published image runtime service
