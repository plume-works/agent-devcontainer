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
fail the create phase over a file it cannot read.

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

### Requirement: a CI job that needs agentdev skills installs them from its checkout

A GitHub Actions `container:` job that invokes an `agentdev:*` skill SHALL check
out the branch and run `agentdev-runtime lifecycle created`,
`agentdev-runtime lifecycle ready --no-wait`, and
`agentdev-runtime lifecycle attached` before the agent starts, so the catalog it
uses is the one on the branch. The job SHALL set `DEV_WORKSPACE_FOLDER` to the
checkout, set `UV_PROJECT_ENVIRONMENT` outside the checkout, create
`/root/.claude`, and set `AGENTDEV_SKIP_PRE_COMMIT`. The settings handed to
`claude-code-action` SHALL deep-merge the hook-written user settings beneath
`.claude/settings.json` and `.claude/settings.local.json`.

#### Scenario: a pull request changes a skill

- **WHEN** the AI review job reviews a pull request that edits the `pr-review`
  skill
- **THEN** the review runs the edited skill from the checkout

#### Scenario: the review job syncs the project

- **WHEN** the lifecycle commands run `uv sync` in the review job
- **THEN** no `.venv` is created inside the checkout under review

#### Scenario: the action receives the settings

- **WHEN** `claude-code-action` starts with the merged settings
- **THEN** the hook-enabled `agentdev` plugin is still enabled

### Requirement: Claude Code and OpenCode are the only supported harnesses

The images SHALL NOT install the Codex CLI, and the runtime SHALL write no Codex
configuration, hooks, credential links, or `CODEX_HOME`. The catalog SHALL ship a
Claude Code plugin and an OpenCode bridge plugin and nothing for Codex, catalog
installs SHALL register Claude Code and OpenCode only, and CI SHALL validate the
catalog with `--require-marketplace claude`. `validate_agent_files` SHALL keep its
`codex` ecosystem for other repositories.

#### Scenario: a container starts

- **WHEN** a runtime container runs its create phase
- **THEN** the catalog is registered for Claude Code and OpenCode, and no Codex
  configuration is written

### Requirement: no code-graph index ships

The images, the runtime, and the catalog SHALL ship no code-graph daemon, MCP
server, hook, or index.

#### Scenario: an agent orients in the repository

- **WHEN** an agent session starts in a runtime container
- **THEN** no code-graph MCP server or hook is configured for it

## Rationale

### CI uses the branch's catalog through the lifecycle commands

A `container:` job runs no lifecycle hooks, and an agent asked for a skill that
does not resolve improvises rather than failing, so a review gated by a required
check would turn green over an ungrounded review. Running all three phases puts
the branch's own catalog in place: the attach phase installs the checkout's
catalog, so the skill under review reviews itself as changed. A `container:` job
applies none of `devcontainer.json`'s `containerEnv` or mounts, which is why the
job supplies them; unset, `UV_PROJECT_ENVIRONMENT` lets `uv sync` write `.venv`
into the reviewed tree while the job stays green. `claude-code-action` merges its
`settings:` input one level deep, so an `enabledPlugins` there would replace the
hook-written object and leave the plugin installed but disabled; this repository
cannot observe that, because its local-scope install also writes
`settings.local.json`, which a consumer never has. `pre-commit install
--install-hooks` is the lifecycle's one expensive step and a review job never
commits.

Rejected:

- **Install from an explicit workflow step.** It duplicates logic the hooks own
  and drifts from them.
- **Run the responder on a bare runner.** It gives up the project toolchain that
  grounds a review.
- **Vendor a repository-local `pr-review` skill.** It forks from the catalog's
  copy and drifts.

### Claude Code and OpenCode only

The maintainer chose Claude Code and OpenCode as the supported harnesses. The
`chatgpt-codex-connector[bot]` GitHub actor is a third-party reviewer, not a
harness, so workflows that recognize it stay. A user may still install Codex in
a container; nothing configures it.

Rejected:

- **Keep `.codex-plugin/plugin.json` as an untested package.** Codex loads
  catalog agents only through generated TOML agents, so without that installer
  the package would ship broken.

### No code-graph index

The maintainer removed codebase-memory-mcp (CBM) on usage evidence: across 386
Claude Code sessions on this repository and Dr.QP no agent called it, although
it was advertised in every session; in 120 controlled runs every setup found the
same lines with or without it, and agents told to use it spent 24–56% more with
Sonnet 5.5 and 29–36% more with Opus 5.5 and verified its answers with `grep`
anyway. The graph also missed virtual C++ dispatch and cross-package Python
calls on untyped receivers. CBM's `install` wrote into user configuration that
outlives the image, and a hook naming a missing binary fails every tool call,
which is why the create phase purges it; `cbm_purge` can go once no supported
instance can still hold a CBM install.

Rejected:

- **Keep the MCP server opt-in.** A pinned binary and its upgrades for a tool no
  run chose unprompted.
- **Require a manual `uninstall` before upgrading.** Anyone who missed it would
  get a failing hook on every tool call.
