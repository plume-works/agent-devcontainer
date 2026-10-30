---
type: feature
stage: implemented
description: A dedicated agentdev-deploy image starts a persistent single-project agent environment with OpenCode, nested Docker, CBM, keyring, and Xpra without a Dev Containers client.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-29T21:00:00Z
sources:
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: docker/base/agentdev-base.Dockerfile
- resource: .devcontainer/scripts/opencode-web-start.sh
- resource: .devcontainer/devcontainer.json
- resource: .github/workflows/ci.yml
---

# Standalone OpenCode container

## Purpose

Publish `ghcr.io/plume-works/agentdev-deploy` as a dedicated, self-starting
image for one project or worktree. Operators can use it without a Dev Containers
client, Coder, or this repository's scaffolding in the project checkout.

## Behaviour

- Derive the image from `agentdev-base` and share the runtime primitives with
  the `agentdev-devcontainer` image.
- Accept a mounted checkout or clone a configured repository into a persistent
  workspace volume. Reuse an existing checkout without automatic Git updates.
- Start nested Docker, CBM, an instance-local D-Bus/keyring, and Xpra. Start
  OpenCode only after required services, initial indexing, and matching project
  preparation succeed. Run uv sync and install pre-commit hooks when their
  project configuration exists.
- Supervise required services individually, retry failures with bounded backoff,
  and exit the container if recovery is exhausted.
- Keep Claude Code and Codex available, including catalog and auth setup,
  without automatically starting either interface. Prefer a checkout-provided
  agentdev catalog when present; otherwise use the image-bundled catalog.
- Run agent tools as a configurable numeric UID/GID, default `1000:1000`, with
  passwordless sudo. Containers sharing agent credentials use the same UID/GID.
- Share Claude/Codex credentials; keep OpenCode logins, sessions, configuration,
  keyrings, caches, and Docker storage per instance. Support injected GitHub
  tokens without adding an interactive GitHub-login persistence facility.
- Connect to an existing external reverse proxy without publishing host ports.
  OpenCode retains server-password authentication; the proxy owns Xpra access
  authentication. Start Xpra by default, with an explicit disable option.
- Keep the firewall opt-in and retain existing nested-Docker image cleanup and
  BuildKit garbage collection.
- Supply optional Compose configuration that creates project volumes and a
  consistently named shared agent-auth volume. Omit the Docker MCP gateway,
  Docker Desktop secrets integration, and host Docker socket mounts.

## Edge cases

- Fresh state, persistent state, and image upgrades must all reconcile managed
  configuration while preserving user customizations and sessions.
- An incompatible UID/GID on shared credentials must fail without changing
  another running container's credential ownership.
- A nonempty invalid workspace, unavailable worktree Git metadata, failed
  preparation, or missing required service must produce an actionable failure.
- Restarting a dirty checkout must preserve its branch, tracked changes, and
  user files; project preparation is limited to its expressly supported changes.
- Two project containers may share Claude/Codex credentials but must not share
  OpenCode logins, session databases, keyring databases, Docker engines, or
  instance caches.
- Service crashes and container termination require bounded recovery and clean
  process shutdown, including daemonizing tools.

## Open questions

No product choices remain open. The implementation must verify CBM lifecycle and
ownership compatibility, non-root tool availability, and supervised DinD
operation on both supported architectures before accepting the runtime.
