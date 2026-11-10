# Catalog lifecycle Specification

## Purpose

When and how the agentdev catalog gets installed into the persistent Claude plugin state and the OpenCode user config — during the agentdev-base build and again by the agentdev-devcontainer postCreateCommand.

## Requirements

### Requirement: the catalog is installed at image build time and again by postCreateCommand

The `agentdev` catalog staged at `$AGENTDEV_CATALOG_DIR` SHALL be installed into
each agent's plugin state during the `agentdev-base` build, at Claude user scope
and by registering the catalog's OpenCode bridge plugin in the user's OpenCode
config, so a consumer that runs the image without lifecycle commands resolves
`agentdev:*` skills. `agentdev-devcontainer`'s `postCreateCommand` SHALL also
install it, because a mounted `~/.claude` volume shadows what the image build
wrote. Because the build-time Claude install seeds a real `/root/.claude.json`
into the image, `postCreateCommand` SHALL establish the
volume→`/root/.claude.json` symlink — discarding the image's real file, seeding
`/root/.claude/claude.json` with `{}` only when the volume has none — so the
mounted `agentdev-claude` volume remains the source of truth for `claude.json`
and no image content is folded into it.

#### Scenario: the image runs with no volumes and no lifecycle hooks

- **WHEN** a container starts from `agentdev-base` without client-state volumes
  and no lifecycle command runs
- **THEN** the catalog installed during the image build is present, an
  `agentdev:*` skill resolves in Claude Code, and OpenCode loads the staged
  bridge plugin and lists the catalog's skills.

#### Scenario: a devcontainer starts for the first time on a fresh volume

- **WHEN** `postCreateCommand` runs, `$AGENTDEV_CATALOG_DIR` exists, and the
  image ships a real `/root/.claude.json`
- **THEN** `postCreateCommand` discards that image file and symlinks
  `/root/.claude.json` to a freshly-seeded `/root/.claude/claude.json`, so the
  volume's `claude.json` holds no image content, and the staged catalog is
  installed into the fresh `agentdev-claude` volume at Claude user scope and
  into the OpenCode user config.

#### Scenario: a devcontainer starts with a catalog already installed on its volume

- **WHEN** the `agentdev-claude` volume already contains a prior install and
  `claude.json` (it persists per devcontainer instance), and the recreated
  container carries the image's `/root/.claude.json`
- **THEN** `postCreateCommand` discards the image's `/root/.claude.json` and
  symlinks `/root/.claude.json` to the volume's existing `claude.json`, so that
  content is preserved (Claude may append bootstrap fields, so the guarantee is
  content preservation, not byte-identity), the volume mount shadows the
  image-build catalog install, and `postCreateCommand` re-applies that install
  every time the container is created, so it is never silently stale.

### Requirement: the create phase clears codebase-memory-mcp's leftovers

The create phase of both profiles SHALL remove what
`codebase-memory-mcp install` wrote into persisted configuration, after
`~/.claude.json` is linked: its hooks in Claude's `settings.json`, its MCP
entries in `claude.json` and OpenCode's config, its marked blocks in OpenCode's
`AGENTS.md` and `plugins/cbm-augment.ts`, its agents, skill, and hook scripts,
and its binary and cache in the home. It SHALL leave every other entry and file
in place, SHALL NOT rewrite a file that holds nothing of CBM's, and SHALL NOT
fail the create phase over a file it cannot read. The decision is [No code-graph
index](#rationale).

#### Scenario: a volume holds a CBM install beside the user's configuration

- **WHEN** the create phase runs on a volume holding CBM's hooks and entries
  next to the user's own hooks, MCP servers, agents, and instructions
- **THEN** only CBM's are removed, and `~/.claude.json` stays a symlink.

#### Scenario: a home holds nothing of CBM's

- **WHEN** the create phase runs on a home with no CBM install
- **THEN** no file is rewritten or created.

#### Scenario: a configuration file cannot be read

- **WHEN** a file the cleanup edits is malformed
- **THEN** that file is left as it is, a warning names the failure, the other
  cleanup steps still run, and the create phase continues.

### Requirement: the staged catalog holds only the plugin catalog

The staged catalog at `$AGENTDEV_CATALOG_DIR` SHALL contain `.claude-plugin/`
and `.agents/plugins/` and SHALL NOT contain any plugin `tests/` directory or
the `.agents/` root instruction files.

#### Scenario: the catalog is staged

- **WHEN** the image stages the catalog at `$AGENTDEV_CATALOG_DIR`
- **THEN** it holds `.claude-plugin/` and `.agents/plugins/`, and no plugin
  `tests/` directory or `.agents/` root instruction file

### Requirement: this repository's own checkout overrides the staged catalog on attach

The attach lifecycle SHALL register this checkout's complete Claude and OpenCode
catalog over the staged copy and SHALL leave the staged copy selected when the
mounted repository does not contain a complete catalog. A complete catalog SHALL
consist of `.claude-plugin/marketplace.json` and the OpenCode bridge directory.

#### Scenario: an agentdev developer reloads the editor

- **WHEN** this checkout's catalog changed and attach runs
- **THEN** all clients resolve the checkout version without an image rebuild.

#### Scenario: a normal consumer attaches

- **WHEN** its repository has no complete agentdev catalog
- **THEN** attach succeeds without changing the staged catalog registration.

#### Scenario: a checkout with only the Claude manifest and the OpenCode bridge

- **WHEN** the checkout holds `.claude-plugin/marketplace.json` and the OpenCode
  bridge but no `.agents/plugins/marketplace.json`, and attach runs
- **THEN** the checkout catalog is registered over the staged copy.

### Requirement: only agent credentials are shared across worktrees

The `agentdev-agents-auth` volume SHALL hold only each agent's authentication
state (mounted at `/root/.agents-auth/<agent>`); all other plugin/install state
lives in the per-devcontainer-instance `agentdev-claude` / `agentdev-opencode`
volumes.

#### Scenario: two worktrees of the same repository are opened as separate devcontainers

- **WHEN** both attach
- **THEN** each gets its own catalog install (scoped per instance) but shares
  the same logged-in Claude credentials (scoped to the shared auth volume).

### Requirement: standalone startup selects and reconciles the runtime catalog

Standalone `agentdev-deploy` startup SHALL use a valid checkout-provided
agentdev catalog when present and otherwise the immutable image catalog. It
SHALL reconcile Claude and OpenCode configuration as the runtime user after
mounts and before OpenCode starts, without removing unrelated user settings. A
registration already matching the selected catalog SHALL be left in place
without rewriting client configuration. A failed reconciliation SHALL mark the
runtime degraded and SHALL NOT stop OpenCode from starting, unless strict
startup is selected.

#### Scenario: the project provides the catalog

- **WHEN** the checkout contains the required catalog manifests and bridge
- **THEN** both clients use that checkout catalog for the container start.

#### Scenario: a catalog is absent or the image is upgraded

- **WHEN** a checkout has no catalog or a newer bundled catalog is selected
- **THEN** startup applies the selected bundled catalog over stale managed
  registrations and preserves unrelated configuration.

#### Scenario: the container restarts with an unchanged catalog

- **WHEN** startup selects the catalog that is already registered
- **THEN** every client's configuration file is byte-identical afterwards.
