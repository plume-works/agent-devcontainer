---
type: spec
description: The agentdev-deploy image runs one persistent project without Coder or a Dev Containers client, under a configurable non-root identity, with supervised bounded recovery, a latched failed or degraded state with explicit retry, and browser access only through an external proxy.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/supervisor.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/remote_control.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/workspace.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/health.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/docker.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/firewall.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/project.py
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: docker/deploy/supervisord.conf
- resource: compose.opencode.yml
- resource: compose.opencode.bind.yml
- resource: py_packages/agentdev_runtime/agentdev_runtime/opencode.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/settings.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/xpra.py
---

# Standalone OpenCode runtime

The single-project runtime of the `agentdev-deploy` image. OpenCode web,
[Devcontainer Git credentials](devcontainer-git-credentials.md), and
[Devcontainer Docker storage](devcontainer-docker-storage.md) keep their
integration-specific requirements; the standalone requirements below do not
change Coder's tmux/failure semantics.

## Requirements

### Requirement: a dedicated image owns a single-project runtime

`ghcr.io/plume-works/agentdev-deploy` SHALL derive from the corresponding digest
of `agentdev-base`, provide linux/amd64 and linux/arm64 images, and start its
environment without Coder, a Dev Containers client, or project scaffolding. It
SHALL keep Claude Code available without autostarting it, except Claude Remote
Control when `AGENTDEV_CLAUDE_RC_MODE` opts in, and SHALL NOT install Codex.

#### Scenario: an ordinary checkout is mounted

- **WHEN** an operator starts the dedicated image with valid required
  configuration
- **THEN** it prepares that single project and starts OpenCode and its required
  services using image-owned shared helpers.

#### Scenario: the base image is used

- **WHEN** an existing consumer starts `agentdev-base` or runs its own copied
  devcontainer hooks on it
- **THEN** it keeps the lifecycle-neutral base's command defaults, Coder
  integration, opt-outs, and lifecycle failure semantics, and no deploy runtime
  starts.

### Requirement: startup prepares or reuses one workspace

The runtime SHALL support a bind-mounted checkout or first clone into an empty
persistent workspace, defaulting to /workspaces/project. It SHALL preserve an
existing checkout without fetch, pull, reset, clean, branch switching, or
ownership migration. It SHALL authenticate supported GitHub HTTPS operations
with injected GH_TOKEN/GITHUB_TOKEN, and it SHALL NOT store those tokens. Only a
start that clones configures this authentication; a start that reuses a checkout
does not: [Bug: a deploy runtime that reuses a checkout does not configure the
git credential helper](../bugs/reused-checkout-gets-no-credential-helper.md). It
SHALL run the applicable uv synchronization and register pre-commit's Git hook
scripts. It SHALL NOT build hook environments. None of these SHALL delay
OpenCode, and their failure SHALL mark the runtime degraded. If the runtime
cannot use a checkout, the runtime SHALL latch its state as failed.

#### Scenario: the first clone is private

- **WHEN** an empty destination, repository URL, and valid injected token are
  supplied
- **THEN** startup configures noninteractive HTTPS authentication before cloning
  and prepares the checkout without logging the token.

#### Scenario: a dirty checkout restarts

- **WHEN** the workspace has local edits and a selected branch
- **THEN** startup preserves the branch and edits, performs only the supported
  project preparation, and does not automatically contact Git remotes.

#### Scenario: the checkout cannot be used

- **WHEN** required worktree metadata is absent, a nonempty destination is
  invalid, or the clone fails
- **THEN** the runtime latches failed, records the cause, keeps OpenCode
  unavailable, and does not restart or rerun preparation.

#### Scenario: optional preparation fails

- **WHEN** a custom hook conflicts, uv synchronization fails, or catalog
  registration fails
- **THEN** OpenCode starts and serves, and the runtime reports degraded, naming
  the failed step and its retry command.

#### Scenario: hook environments need the network

- **WHEN** the project's pre-commit hooks would download toolchains or packages
  to build their environments
- **THEN** startup registers the hook scripts without building any environment
  and contacts no hook source.
