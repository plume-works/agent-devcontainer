---
type: spec
description: When and how the agentdev catalog gets installed into the persistent Claude/Codex plugin state and the OpenCode user config — during the agentdev-base build and again by the agentdev-devcontainer postCreateCommand.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T20:55:00Z
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/catalog.py
- resource: .agents/plugins/agentdev/bin/install-codex-agents.py
- resource: ansible/roles/agentic_tools/tasks/install_catalog.yml
- resource: docker/base/agentdev-base.Dockerfile
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: README.md
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/workspace.py
---

# Catalog lifecycle

## Requirement: the catalog is installed at image build time and again by postCreateCommand

The `agentdev` catalog staged at `$AGENTDEV_CATALOG_DIR` SHALL be installed into
each agent's plugin state during the `agentdev-base` build, at Claude user
scope, via Codex's own registration, and by registering the catalog's OpenCode
bridge plugin in the user's OpenCode config, so a consumer that runs the image
without lifecycle commands resolves `agentdev:*` skills.
`agentdev-devcontainer`'s `postCreateCommand` SHALL also install it, because a
mounted `~/.claude` / `~/.codex` volume shadows what the image build wrote.
Because the build-time Claude install seeds a real `/root/.claude.json` into the
image, `postCreateCommand` SHALL establish the volume→`/root/.claude.json`
symlink before CBM is configured — discarding the image's real file, seeding
`/root/.claude/claude.json` with `{}` only when the volume has none — so the
mounted `agentdev-claude` volume remains the source of truth for `claude.json`,
the CBM install folds its MCP entry back into the volume, and no image content
is folded into it.

### Scenario: the image runs with no volumes and no lifecycle hooks

- **WHEN** a container starts from `agentdev-base` without client-state volumes
  and no lifecycle command runs
- **THEN** the catalog installed during the image build is present, an
  `agentdev:*` skill resolves in Claude Code and Codex, and OpenCode loads the
  staged bridge plugin and lists the catalog's skills.

### Scenario: a devcontainer starts for the first time on a fresh volume

- **WHEN** `postCreateCommand` runs, `$AGENTDEV_CATALOG_DIR` exists, and the
  image ships a real `/root/.claude.json`
- **THEN** `postCreateCommand` discards that image file and symlinks
  `/root/.claude.json` to a freshly-seeded `/root/.claude/claude.json` before
  CBM is configured, so the CBM install folds only its MCP entry into the
  volume's clean `claude.json` with no image content, and the staged catalog is
  installed into the fresh `agentdev-claude` / `agentdev-codex` volumes at
  Claude user scope and into the OpenCode user config.

### Scenario: a devcontainer starts with a catalog already installed on its volume

- **WHEN** the `agentdev-claude` / `agentdev-codex` volumes already contain a
  prior install and `claude.json` (they persist per devcontainer instance), and
  the recreated container carries the image's `/root/.claude.json`
- **THEN** `postCreateCommand` discards the image's `/root/.claude.json` and
  symlinks `/root/.claude.json` to the volume's existing `claude.json` before
  CBM is configured, so that content is preserved (the CBM install folds its MCP
  entry back in; Claude may append bootstrap fields, so the guarantee is content
  preservation, not byte-identity), the volume mount shadows the image-build
  catalog install, and `postCreateCommand` re-applies that install every time
  the container is created, so it is never silently stale.

## Requirement: this repository's own checkout overrides the staged catalog on attach

The attach lifecycle SHALL register this checkout's complete Claude, Codex, and
OpenCode catalog over the staged copy and SHALL leave the staged copy selected
when the mounted repository does not contain a complete catalog.

### Scenario: an agentdev developer reloads the editor

- **WHEN** this checkout's catalog changed and attach runs
- **THEN** all clients resolve the checkout version without an image rebuild.

### Scenario: a normal consumer attaches

- **WHEN** its repository has no complete agentdev catalog
- **THEN** attach succeeds without changing the staged catalog registration.

## Requirement: Codex receives the catalog agents as generated TOML agents

Every Codex install of the catalog — at image build, by postCreateCommand, and
on attach — SHALL write one `agentdev-<stem>.toml` agent per
`agents/<stem>.agent.md` into `${CODEX_HOME:-~/.codex}/agents/`, named `<stem>`,
carrying the file's description and body, with `sandbox_mode` `workspace-write`
when the agent's tools include `Edit` or `Write` and `read-only` otherwise. It
SHALL remove every `agentdev-*.toml` there that the current catalog does not
produce, and SHALL NOT modify any other file in that directory.

### Scenario: the catalog is installed into Codex

- **WHEN** `agentdev-runtime catalog install` or the image build installs a
  catalog whose `agents/` holds `durable-knowledge-auditor.agent.md`
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
lives in the per-devcontainer-instance `agentdev-claude` / `agentdev-codex` /
`agentdev-opencode` volumes.

### Scenario: two worktrees of the same repository are opened as separate devcontainers

- **WHEN** both attach
- **THEN** each gets its own catalog install (scoped per instance) but shares
  the same logged-in Claude/Codex/OpenCode credentials (scoped to the shared
  auth volume).

## Requirement: standalone startup selects and reconciles the runtime catalog

Standalone `agentdev-deploy` startup SHALL use a valid checkout-provided
agentdev catalog when present and otherwise the immutable image catalog. It
SHALL reconcile Claude, Codex, and OpenCode configuration as the runtime user
after mounts and before OpenCode starts, including generated Codex agents,
without removing unrelated user settings or agents. A registration already
matching the selected catalog SHALL be left in place without rewriting client
configuration. A failed reconciliation SHALL mark the runtime degraded and SHALL
NOT stop OpenCode from starting, unless strict startup is selected.

### Scenario: the project provides the catalog

- **WHEN** the checkout contains the required catalog manifests and bridge
- **THEN** all three clients use that checkout catalog for the container start.

### Scenario: a catalog is absent or the image is upgraded

- **WHEN** a checkout has no catalog or a newer bundled catalog is selected
- **THEN** startup applies the selected bundled catalog over stale managed
  registrations and preserves unrelated configuration.

### Scenario: the container restarts with an unchanged catalog

- **WHEN** startup selects the catalog that is already registered
- **THEN** every client's configuration file is byte-identical afterwards.
