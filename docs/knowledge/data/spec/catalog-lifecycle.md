---
type: spec
description: When and how the agentdev catalog gets installed into the persistent Claude plugin state and the OpenCode user config — during the agentdev-base build and again by the agentdev-devcontainer postCreateCommand.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/catalog.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/cbm_purge.py
- resource: ansible/roles/agent_catalog/tasks/install_catalog.yml
- resource: ansible/roles/agent_catalog/tasks/stage_catalog.yml
- resource: docker/base/agentdev-base.Dockerfile
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: README.md
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/workspace.py
---

# Catalog lifecycle

## Requirement: the catalog is installed at image build time and again by postCreateCommand

The `agentdev` catalog staged at `$AGENTDEV_CATALOG_DIR` SHALL be installed into
each agent's plugin state during the `agentdev-base` build, at Claude user scope
and by registering the catalog's OpenCode bridge plugin in the user's OpenCode
config, so a consumer that runs the image without lifecycle commands resolves
`agentdev:*` skills. `agentdev-devcontainer`'s create phase SHALL also install
it into the runtime account's home volume, which starts empty and receives no
image content. `~/.claude.json` SHALL be a regular file on that volume.

### Scenario: the image runs with no volumes and no lifecycle hooks

- **WHEN** a container starts from `agentdev-base` without client-state volumes
  and no lifecycle command runs
- **THEN** the catalog installed during the image build is present, an
  `agentdev:*` skill resolves in Claude Code, and OpenCode loads the staged
  bridge plugin and lists the catalog's skills.

### Scenario: a devcontainer starts for the first time on a fresh home volume

- **WHEN** the create phase runs, `$AGENTDEV_CATALOG_DIR` exists, and the home
  volume is empty
- **THEN** the staged catalog is installed at Claude user scope and into the
  OpenCode user config on the home volume, and `~/.claude.json` is a regular
  file holding no image content.

### Scenario: a devcontainer starts with a catalog already installed on its home volume

- **WHEN** the home volume already holds a prior install and `~/.claude.json`,
  and the container is recreated
- **THEN** `~/.claude.json`'s content is preserved (Claude may append bootstrap
  fields, so the guarantee is content preservation, not byte-identity), and the
  create phase re-applies the catalog install every time the container is
  created, so it is never silently stale.

### Scenario: a home volume still holds the ~/.claude.json link

- **WHEN** `~/.claude.json` is a symlink to `~/.claude/claude.json`
- **THEN** it is replaced by a regular file with the link target's content, and
  the target is removed.

## Requirement: the create phase clears codebase-memory-mcp's leftovers

The create phase of both profiles SHALL remove what
`codebase-memory-mcp install` wrote into persisted configuration, after any
`~/.claude.json` link is replaced by a regular file: its hooks in Claude's
`settings.json`, its MCP entries in `claude.json` and OpenCode's config, its
marked blocks in OpenCode's `AGENTS.md` and `plugins/cbm-augment.ts`, its
agents, skill, and hook scripts, and its binary and cache in the home. It SHALL
leave every other entry and file in place, SHALL NOT rewrite a file that holds
nothing of CBM's, and SHALL NOT fail the create phase over a file it cannot
read. The decision is [No code-graph index](../architecture/no-code-graph.md).

### Scenario: a volume holds a CBM install beside the user's configuration

- **WHEN** the create phase runs on a volume holding CBM's hooks and entries
  next to the user's own hooks, MCP servers, agents, and instructions
- **THEN** only CBM's are removed.

### Scenario: a home holds a CBM entry behind the ~/.claude.json link

- **WHEN** `~/.claude.json` is a symlink to a file holding CBM's MCP entry
- **THEN** `~/.claude.json` is a regular file without that entry, and the user's
  other content is preserved.

### Scenario: a home holds nothing of CBM's

- **WHEN** the create phase runs on a home with no CBM install
- **THEN** no file is rewritten or created.

### Scenario: a configuration file cannot be read

- **WHEN** a file the cleanup edits is malformed
- **THEN** that file is left as it is, a warning names the failure, the other
  cleanup steps still run, and the create phase continues.

## Requirement: the staged catalog holds only the plugin catalog

The staged catalog at `$AGENTDEV_CATALOG_DIR` SHALL contain `.claude-plugin/`
and `.agents/plugins/` and SHALL NOT contain any plugin `tests/` directory or
the `.agents/` root instruction files.

## Requirement: this repository's own checkout overrides the staged catalog on attach

The attach lifecycle SHALL register this checkout's complete Claude and OpenCode
catalog over the staged copy and SHALL leave the staged copy selected when the
mounted repository does not contain a complete catalog. A complete catalog SHALL
consist of `.claude-plugin/marketplace.json` and the OpenCode bridge directory.

### Scenario: an agentdev developer reloads the editor

- **WHEN** this checkout's catalog changed and attach runs
- **THEN** all clients resolve the checkout version without an image rebuild.

### Scenario: a normal consumer attaches

- **WHEN** its repository has no complete agentdev catalog
- **THEN** attach succeeds without changing the staged catalog registration.

### Scenario: a checkout with only the Claude manifest and the OpenCode bridge

- **WHEN** the checkout holds `.claude-plugin/marketplace.json` and the OpenCode
  bridge but no `.agents/plugins/marketplace.json`, and attach runs
- **THEN** the checkout catalog is registered over the staged copy.

## Requirement: only agent credentials are shared across worktrees

The shared auth volume SHALL hold only Claude's authentication state, mounted at
`/var/lib/agentdev/auth/<agent>`, and SHALL be named after the host user's UID
and GID, so only containers whose account has the same IDs share it. All other
client state SHALL live on each instance's home volume.

### Scenario: two worktrees of the same repository are opened as separate devcontainers

- **WHEN** both attach as the same host user
- **THEN** each gets its own catalog install on its own home volume but shares
  the same logged-in Claude credentials on the shared auth volume.

### Scenario: two host users open Dev Containers on one engine

- **WHEN** their UID/GID pairs differ
- **THEN** each container mounts its own auth volume and neither reads the
  other's credentials.

## Requirement: standalone startup selects and reconciles the runtime catalog

Standalone `agentdev-deploy` startup SHALL use a valid checkout-provided
agentdev catalog when present and otherwise the immutable image catalog. It
SHALL reconcile Claude and OpenCode configuration as the runtime user after
mounts and before OpenCode starts, without removing unrelated user settings. A
registration already matching the selected catalog SHALL be left in place
without rewriting client configuration. A failed reconciliation SHALL mark the
runtime degraded and SHALL NOT stop OpenCode from starting, unless strict
startup is selected.

### Scenario: the project provides the catalog

- **WHEN** the checkout contains the required catalog manifests and bridge
- **THEN** both clients use that checkout catalog for the container start.

### Scenario: a catalog is absent or the image is upgraded

- **WHEN** a checkout has no catalog or a newer bundled catalog is selected
- **THEN** startup applies the selected bundled catalog over stale managed
  registrations and preserves unrelated configuration.

### Scenario: the container restarts with an unchanged catalog

- **WHEN** startup selects the catalog that is already registered
- **THEN** every client's configuration file is byte-identical afterwards.
