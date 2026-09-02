---
type: spec
description: When and how the agentdev catalog gets installed into the persistent Claude/Codex plugin state — at image build time and again by postCreateCommand.
generated:
  by: claude-code/opus-5
  at: 2026-09-02T00:00:00Z
sources:
- resource: .devcontainer/scripts/postCreateCommand.sh
- resource: .devcontainer/scripts/postAttachCommand.sh
- resource: ansible/roles/agentic_tools/tasks/install_catalog.yml
- resource: docker/desktop/agent-desktop.Dockerfile
- resource: README.md
---

# Catalog lifecycle

## Requirement: the catalog is installed at image build time and again by postCreateCommand

The `agentdev` catalog staged at `$AGENTDEV_CATALOG_DIR` SHALL be installed into
each agent's plugin state during the image build, at Claude user scope and via
Codex's own registration, so a consumer that runs the image without devcontainer
lifecycle hooks resolves `agentdev:*` skills. `postCreateCommand.sh` SHALL also
install it, because a mounted `~/.claude` / `~/.codex` volume shadows what the
image build wrote. Because the build-time Claude install seeds a real
`/root/.claude.json` into the image, `postCreateCommand.sh` SHALL establish the
volume→`/root/.claude.json` symlink before `codebase-memory-mcp-install.sh` runs
— discarding the image's real file, seeding `/root/.claude/claude.json` with
`{}` only when the volume has none — so the mounted `agentdev-claude` volume
remains the source of truth for `claude.json`, cbm-install folds its MCP entry
back into the volume, and no image content is folded into it.

### Scenario: the image runs with no volumes and no lifecycle hooks

- **WHEN** a container starts from `ghcr.io/plume-works/agent-desktop` and no
  lifecycle hook runs
- **THEN** the catalog installed during the image build is present, and an
  `agentdev:*` skill resolves.

### Scenario: a devcontainer starts for the first time on a fresh volume

- **WHEN** `postCreateCommand` runs, `$AGENTDEV_CATALOG_DIR` exists, and the
  image ships a real `/root/.claude.json`
- **THEN** `postCreateCommand` discards that image file and symlinks
  `/root/.claude.json` to a freshly-seeded `/root/.claude/claude.json` before
  `codebase-memory-mcp-install.sh` runs, so cbm-install folds only its MCP entry
  into the volume's clean `claude.json` with no image content, and
  `reinstall-agentdev-codex.sh` and `reinstall-agentdev-claude.sh ... user`
  install the staged catalog into the fresh `agentdev-claude` / `agentdev-codex`
  volumes.

### Scenario: a devcontainer starts with a catalog already installed on its volume

- **WHEN** the `agentdev-claude` / `agentdev-codex` volumes already contain a
  prior install and `claude.json` (they persist per devcontainer instance), and
  the recreated container carries the image's `/root/.claude.json`
- **THEN** `postCreateCommand` discards the image's `/root/.claude.json` and
  symlinks `/root/.claude.json` to the volume's existing `claude.json` before
  cbm-install runs, so that content is preserved (cbm-install folds its MCP
  entry back in; Claude may append bootstrap fields, so the guarantee is content
  preservation, not byte-identity), the volume mount shadows the image-build
  catalog install, and `postCreateCommand` re-applies that install every time
  the container is created, so it is never silently stale.

## Requirement: this repository's own checkout overrides the staged catalog on attach

`postAttachCommand.sh` SHALL re-run `reinstall-agentdev-codex.sh` and
`reinstall-agentdev-claude.sh` with no catalog-dir argument on every editor
attachment (including after a window reload), registering this workspace's
`.agents/plugins/agentdev/` over the image's staged copy.

### Scenario: a skill or agent is edited in this checkout and the editor window is reloaded

- **WHEN** the developer reloads the VS Code window (or reattaches)
- **THEN** `postAttachCommand` re-registers the marketplace from
  `.agents/plugins/agentdev/` in the workspace, so the edited skill is picked up
  without a container rebuild.

### Scenario: a consuming project (not this repository) attaches

- **WHEN** `postAttachCommand`'s reinstall scripts run in a consumer project
  that has no `.agents/plugins/agentdev/` marketplace manifest
- **THEN** the scripts find no manifest and exit quietly, leaving the
  image-staged catalog in place.

## Requirement: only agent credentials are shared across worktrees

The `agentdev-agents-auth` volume SHALL hold only each agent's authentication
state (mounted at `/root/.agents-auth/<agent>`); all other plugin/install state
lives in the per-devcontainer-instance `agentdev-claude` / `agentdev-codex`
volumes.

### Scenario: two worktrees of the same repository are opened as separate devcontainers

- **WHEN** both attach
- **THEN** each gets its own catalog install (scoped per instance) but shares
  the same logged-in Claude/Codex credentials (scoped to the shared auth
  volume).
