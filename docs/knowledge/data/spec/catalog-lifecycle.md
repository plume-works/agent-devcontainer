---
type: spec
description: When and how the agentdev catalog gets installed into the persistent Claude/Codex plugin state and the OpenCode user config — at image build time and again by postCreateCommand.
generated:
  by: claude-code/opus-5-5
  at: 2026-10-08T12:00:00Z
sources:
- resource: .devcontainer/scripts/postCreateCommand.sh
- resource: .devcontainer/scripts/postAttachCommand.sh
- resource: .devcontainer/scripts/reinstall-agentdev-opencode.sh
- resource: .devcontainer/scripts/reinstall-agentdev-codex.sh
- resource: .agents/plugins/agentdev/bin/install-codex-agents.py
- resource: ansible/roles/agentic_tools/tasks/install_catalog.yml
- resource: docker/desktop/agent-desktop.Dockerfile
- resource: README.md
---

# Catalog lifecycle

## Requirement: the catalog is installed at image build time and again by postCreateCommand

The `agentdev` catalog staged at `$AGENTDEV_CATALOG_DIR` SHALL be installed into
each agent's plugin state during the image build, at Claude user scope, via
Codex's own registration, and by registering the catalog's OpenCode bridge
plugin in the user's OpenCode config, so a consumer that runs the image without
devcontainer lifecycle hooks resolves `agentdev:*` skills.
`postCreateCommand.sh` SHALL also install it, because a mounted `~/.claude` /
`~/.codex` volume shadows what the image build wrote. Because the build-time
Claude install seeds a real `/root/.claude.json` into the image,
`postCreateCommand.sh` SHALL establish the volume→`/root/.claude.json` symlink
before `codebase-memory-mcp-install.sh` runs — discarding the image's real file,
seeding `/root/.claude/claude.json` with `{}` only when the volume has none — so
the mounted `agentdev-claude` volume remains the source of truth for
`claude.json`, cbm-install folds its MCP entry back into the volume, and no
image content is folded into it.

### Scenario: the image runs with no volumes and no lifecycle hooks

- **WHEN** a container starts from `ghcr.io/plume-works/agent-desktop` and no
  lifecycle hook runs
- **THEN** the catalog installed during the image build is present, an
  `agentdev:*` skill resolves in Claude Code and Codex, and OpenCode loads the
  staged bridge plugin and lists the catalog's skills.

### Scenario: a devcontainer starts for the first time on a fresh volume

- **WHEN** `postCreateCommand` runs, `$AGENTDEV_CATALOG_DIR` exists, and the
  image ships a real `/root/.claude.json`
- **THEN** `postCreateCommand` discards that image file and symlinks
  `/root/.claude.json` to a freshly-seeded `/root/.claude/claude.json` before
  `codebase-memory-mcp-install.sh` runs, so cbm-install folds only its MCP entry
  into the volume's clean `claude.json` with no image content, and
  `reinstall-agentdev-codex.sh`, `reinstall-agentdev-claude.sh ... user`, and
  `reinstall-agentdev-opencode.sh` install the staged catalog into the fresh
  `agentdev-claude` / `agentdev-codex` volumes and the OpenCode user config.

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

`postAttachCommand.sh` SHALL re-run `reinstall-agentdev-codex.sh`,
`reinstall-agentdev-claude.sh`, and `reinstall-agentdev-opencode.sh` with no
catalog-dir argument on every editor attachment (including after a window
reload), registering this workspace's `.agents/plugins/agentdev/` over the
image's staged copy.

### Scenario: a skill or agent is edited in this checkout and the editor window is reloaded

- **WHEN** the developer reloads the VS Code window (or reattaches)
- **THEN** `postAttachCommand` re-registers the marketplace from
  `.agents/plugins/agentdev/` in the workspace, and points OpenCode's bridge
  entry at the workspace copy, so the edited skill is picked up without a
  container rebuild.

### Scenario: a consuming project (not this repository) attaches

- **WHEN** `postAttachCommand`'s reinstall scripts run in a consumer project
  that has no `.agents/plugins/agentdev/` marketplace manifest or bridge plugin
- **THEN** the scripts find nothing to register and exit quietly, leaving the
  image-staged catalog in place.

## Requirement: Codex receives the catalog agents as generated TOML agents

Every Codex install of the catalog — at image build, by postCreateCommand, and
on attach — SHALL write one `agentdev-<stem>.toml` agent per
`agents/<stem>.agent.md` into `${CODEX_HOME:-~/.codex}/agents/`, named `<stem>`,
carrying the file's description and body, with `sandbox_mode` `workspace-write`
when the agent's tools include `Edit` or `Write` and `read-only` otherwise. It
SHALL remove every `agentdev-*.toml` there that the current catalog does not
produce, and SHALL NOT modify any other file in that directory.

### Scenario: the catalog is installed into Codex

- **WHEN** `reinstall-agentdev-codex.sh` or the image build installs a catalog
  whose `agents/` holds `durable-knowledge-auditor.agent.md`
- **THEN** Codex lists `durable-knowledge-auditor` as a spawnable agent type,
  and dispatching it runs the agent file's body with a read-only sandbox.

### Scenario: an agent is removed from the catalog

- **WHEN** a catalog without `tdd-red.agent.md` is installed over one that had
  it
- **THEN** `agentdev-tdd-red.toml` no longer exists and every other catalog
  agent's file is current.

### Scenario: the user has their own Codex agents

- **WHEN** `~/.codex/agents/` holds `codebase-memory.toml` before an install
- **THEN** the file is unchanged after the install.

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
