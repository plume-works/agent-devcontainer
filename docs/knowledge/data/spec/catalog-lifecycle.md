---
type: spec
description: When and how the agentdev catalog gets installed into the persistent Claude/Codex plugin state, and why it can't happen at image build time.
generated:
  by: claude-sonnet-5
  at: 2026-08-12T00:00:00Z
sources:
- .devcontainer/scripts/postCreateCommand.sh
- .devcontainer/scripts/postAttachCommand.sh
- README.md
---

# Catalog lifecycle

## Requirement: catalog install happens in postCreateCommand, not the image build

The `agentdev` catalog staged at `$AGENTDEV_CATALOG_DIR` SHALL be installed into
each agent's plugin state by `postCreateCommand.sh`, at Claude user scope and
via Codex's own registration script — never baked into the image build.

### Scenario: a devcontainer starts for the first time on a fresh volume

- **WHEN** `postCreateCommand` runs and `$AGENTDEV_CATALOG_DIR` exists
- **THEN** `reinstall-agentdev-codex.sh` and
  `reinstall-agentdev-claude.sh ... user` install the staged catalog into the
  newly created `agentdev-claude` / `agentdev-codex` volumes.

### Scenario: a devcontainer starts with a catalog already installed on its volume

- **WHEN** the `agentdev-claude` / `agentdev-codex` volumes already contain a
  prior install (they persist per devcontainer instance)
- **THEN** an image-build-time install would have been shadowed by the volume
  mount; running the install in `postCreateCommand` instead re-applies it every
  time the container is created, so it is never silently stale.

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
