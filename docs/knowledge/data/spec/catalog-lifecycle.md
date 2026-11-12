---
type: spec
description: When and how the agentdev catalog gets installed into the persistent Claude plugin state and the OpenCode user config — during the agentdev-base build, by the agentdev-devcontainer lifecycle phases, by the standalone runtime, per Claude worktree, and in CI agent jobs — and how the create phase clears codebase-memory-mcp's leftovers.
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
- resource: py_packages/agentdev_runtime/agentdev_runtime/worktree.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/project.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/git.py
- resource: .github/actions/run-claude-responder/action.yml
- resource: .claude/.gitignore
- resource: ansible/roles/agentic_tools/defaults/main.yml
- resource: .devcontainer/docker-compose.yml
- resource: py_packages/agentdev_runtime/agentdev_runtime/opencode.py
---

# Catalog lifecycle

## Requirements

### Requirement: the catalog is installed at image build time and again by postCreateCommand

The `agentdev` catalog staged at `$AGENTDEV_CATALOG_DIR` SHALL be installed into
each agent's plugin state during the `agentdev-base` build, at Claude user scope
and by registering the catalog's OpenCode bridge plugin in the user's OpenCode
config, so a consumer that runs the image without lifecycle commands resolves
`agentdev:*` skills. The install step SHALL take the marketplace name from the
staged `.claude-plugin/marketplace.json` and add the marketplace from the staged
path, needing no network access and no authentication. `agentdev-base` SHALL
install OpenCode v2 from the npm package `@opencode/cli` at the version
`agentic_tools_opencode_version` pins. `agentdev-devcontainer`'s create phase
SHALL also install it into the runtime account's home volume, which starts empty
and receives no image content. `~/.claude.json` SHALL be a regular file on that
volume.

#### Scenario: the image runs with no volumes and no lifecycle hooks

- **WHEN** a container starts from `agentdev-base` without client-state volumes
  and no lifecycle command runs
- **THEN** the catalog installed during the image build is present, an
  `agentdev:*` skill resolves in Claude Code, and OpenCode loads the staged
  bridge plugin and lists the catalog's skills.

#### Scenario: a devcontainer starts with a catalog already installed on its home volume

- **WHEN** the home volume already holds a prior install and `~/.claude.json`,
  and the container is recreated
- **THEN** `~/.claude.json`'s content is preserved (Claude may append bootstrap
  fields, so the guarantee is content preservation, not byte-identity), and the
  create phase re-applies the catalog install every time the container is
  created, so it is never silently stale.

#### Scenario: a home volume still holds the ~/.claude.json link

- **WHEN** `~/.claude.json` is a symlink to `~/.claude/claude.json`
- **THEN** it is replaced by a regular file with the link target's content, and
  the target is removed.

### Requirement: the create phase clears codebase-memory-mcp's leftovers

The create phase of both profiles SHALL remove what
`codebase-memory-mcp install` wrote into persisted configuration, after any
`~/.claude.json` link is replaced by a regular file: its hooks in Claude's
`settings.json`, its MCP entries in `claude.json` and OpenCode's config, its
marked blocks in OpenCode's `AGENTS.md` and `plugins/cbm-augment.ts`, its
agents, skill, and hook scripts, and its binary and cache in the home. It SHALL
leave every other entry and file in place, SHALL NOT rewrite a file that holds
nothing of CBM's, and SHALL NOT fail the create phase over a file it cannot
read.

#### Scenario: a home holds a CBM entry behind the ~/.claude.json link

- **WHEN** `~/.claude.json` is a symlink to a file holding CBM's MCP entry
- **THEN** `~/.claude.json` is a regular file without that entry, and the user's
  other content is preserved.

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

### Requirement: this repository's own checkout overrides the staged catalog on attach

The attach lifecycle SHALL register this checkout's complete Claude and OpenCode
catalog over the staged copy, installing the Claude catalog at user scope, and
SHALL leave the staged copy selected when the mounted repository does not
contain a complete catalog. A complete catalog SHALL consist of
`.claude-plugin/marketplace.json` and the OpenCode bridge directory.

#### Scenario: an agentdev developer reloads the editor

- **WHEN** this checkout's catalog changed and attach runs
- **THEN** all clients resolve the checkout version without an image rebuild.

#### Scenario: a checkout with only the Claude manifest and the OpenCode bridge

- **WHEN** the checkout holds `.claude-plugin/marketplace.json` and the OpenCode
  bridge but no `.agents/plugins/marketplace.json`, and attach runs
- **THEN** the checkout catalog is registered over the staged copy.

#### Scenario: the attach install leaves the main checkout's local settings alone

- **WHEN** attach registers a complete checkout catalog
- **THEN** the catalog's plugins are enabled in the user's Claude settings and
  no `enabledPlugins` entry is written to the checkout's
  `.claude/settings.local.json`.

### Requirement: a CI agent job loads the catalog of the branch it checks out

The `run-claude-responder` action SHALL run
`agentdev-runtime lifecycle created`,
`agentdev-runtime lifecycle ready --no-wait`, and
`agentdev-runtime lifecycle attached` against the job's checkout before it
invokes the agent, so a checkout that ships a complete catalog supplies the
`agentdev:*` skills the agent resolves. It SHALL run them with
`AGENTDEV_SKIP_PRE_COMMIT` set, under which the create phase registers no
pre-commit hooks, and with `UV_PROJECT_ENVIRONMENT` outside the checkout. The
create phase SHALL mark the checkout a git safe directory whatever
`AGENTDEV_SKIP_*` variables are set. The settings the action hands to
`claude-code-action` SHALL be the deep merge of the user's
`~/.claude/settings.json`, the checkout's `.claude/settings.json`, and its
`.claude/settings.local.json` when present, in that order, so the plugins the
lifecycle commands enabled stay enabled.

#### Scenario: a pull request changes a skill

- **WHEN** the responder reviews a pull request of this repository that edits an
  `agentdev:*` skill
- **THEN** the agent resolves that skill from the pull request's checkout, not
  from the catalog staged in the image.

#### Scenario: the create phase runs with pre-commit skipped

- **WHEN** `agentdev-runtime lifecycle created` runs with
  `AGENTDEV_SKIP_PRE_COMMIT` set in a checkout that has a
  `.pre-commit-config.yaml`
- **THEN** no `pre-commit install` runs, the rest of the create phase runs, and
  git accepts the checkout as a safe directory.

### Requirement: each Claude worktree of a catalog checkout loads its own catalog

When the standalone runtime registers a checkout's own catalog, it SHALL also
register `agentdev-runtime worktree create` and
`agentdev-runtime worktree remove` as the user's Claude `WorktreeCreate` and
`WorktreeRemove` hooks, as the Dev Container create phase does outside deploy
mode. A worktree that hook creates in a checkout that ships a complete catalog
SHALL load every plugin of its own checkout's catalog from the worktree's
working tree, under a marketplace named `wt-<worktree name>`, and SHALL NOT load
the shared catalog's plugins. The hook SHALL register that marketplace from
`<worktree>/.claude/marketplace.local.json`, a copy of the worktree's
`.claude-plugin/marketplace.json` renamed `wt-<worktree name>`, which git
ignores. It SHALL enable each `<plugin>@wt-<worktree name>` only in the
worktree's `.claude/settings.local.json`, next to each
`<plugin>@<shared marketplace name>` set to `false`, and SHALL leave no
`<plugin>@wt-<worktree name>` key in the main checkout's
`.claude/settings.local.json`. `worktree create` SHALL fail when
`wt-<worktree name>` is already registered from another file, and
`worktree remove` SHALL remove `wt-<worktree name>` only when it is registered
from its own worktree's file, before it removes the worktree and also when the
worktree is already gone. When a step of `worktree create` fails, the hook SHALL
remove the marketplace, worktree, and branch it made and exit non-zero. In every
repository, `worktree create` SHALL merge the main checkout's local
`permissions.allow` rules into the worktree's `.claude/settings.local.json`.

#### Scenario: a Remote Control session spawns in a worktree

- **WHEN** Remote Control in `worktree` spawn mode starts a session in a
  checkout that ships a complete catalog
- **THEN** the session loads `agentdev@wt-<worktree name>` from
  `<worktree>/.agents/plugins/agentdev`, including uncommitted changes there,
  and not `agentdev@agent-devcontainer`.

#### Scenario: a session in the main checkout

- **WHEN** a session starts in the main checkout
- **THEN** it loads the shared catalog, as before.

#### Scenario: a repository without a complete catalog

- **WHEN** the hook creates a worktree of a repository with no complete catalog
- **THEN** the worktree is created at `.claude/worktrees/<name>` on branch
  `worktree-<name>` and no marketplace is registered.

#### Scenario: the worktree is removed

- **WHEN** Claude Code removes a worktree the hook created
- **THEN** its `wt-<worktree name>` marketplace and installs are removed and no
  entry for it remains in the user's Claude settings.

#### Scenario: the worktree's catalog is enabled only in the worktree

- **WHEN** the hook creates a worktree of a checkout that ships a complete
  catalog
- **THEN** the worktree's `.claude/settings.local.json` enables
  `agentdev@wt-<worktree name>` and disables `agentdev@agent-devcontainer`, the
  main checkout's `.claude/settings.local.json` holds no
  `agentdev@wt-<worktree name>` key, and `git status` in the worktree lists no
  file the hook wrote.

#### Scenario: Claude Code removes a worktree that is already gone

- **WHEN** the worktree directory no longer exists and its `wt-<worktree name>`
  marketplace is registered from it
- **THEN** `worktree remove` removes the marketplace and exits zero.

#### Scenario: the main checkout's local settings cannot be read

- **WHEN** the main checkout's `.claude/settings.local.json` is not valid JSON
  and the hook creates a worktree
- **THEN** the hook warns on stderr, copies no rule, and still creates the
  worktree.

### Requirement: only agent credentials are shared across worktrees

The shared auth volume SHALL hold only Claude's authentication state, mounted at
`/var/lib/agentdev/auth/<agent>`, and SHALL be named after the host user's UID
and GID, so only containers whose account has the same IDs share it. All other
client state SHALL live at its default path on each instance's home volume — in
the Dev Container the per-instance `agentdev-home-${devcontainerId}` volume the
image mounts at `/home/agent`. That state includes Claude's configuration,
sessions, and `~/.claude.json`, OpenCode's configuration, and OpenCode's data
directory `~/.local/share/opencode`, which holds its database of provider logins
and sessions and the generated OpenCode server password.

#### Scenario: two worktrees of the same repository are opened as separate devcontainers

- **WHEN** both attach as the same host user
- **THEN** each gets its own catalog install on its own home volume but shares
  the same logged-in Claude credentials on the shared auth volume.

### Requirement: registering a catalog root replaces earlier registrations

`agentdev-runtime catalog install <root>` SHALL uninstall every plugin the
root's `.claude-plugin/marketplace.json` publishes from the `user`, `project`,
and `local` scopes, under the manifest's marketplace name and under any
marketplace already registered from the same root, SHALL remove those
marketplaces, and SHALL then add the root as a marketplace and install every
published plugin at the requested scope. It SHALL leave exactly one bridge entry
in the OpenCode config's `plugin` list, pointing at the root's bridge, replacing
any entry for another root's bridge and keeping every other key and plugin. A
root that ships no Claude manifest or no OpenCode bridge SHALL leave that
client's registration as it was.

### Requirement: standalone startup selects and reconciles the runtime catalog

Standalone `agentdev-deploy` startup SHALL use a valid checkout-provided
agentdev catalog when present and otherwise the immutable image catalog. It
SHALL reconcile Claude and OpenCode configuration as the runtime user after
mounts and before OpenCode starts, without removing unrelated user settings. A
registration already matching the selected catalog SHALL be left in place
without rewriting client configuration. A failed reconciliation SHALL mark the
runtime degraded and SHALL NOT stop OpenCode from starting, unless strict
startup is selected.

#### Scenario: a catalog is absent or the image is upgraded

- **WHEN** a checkout has no catalog or a newer bundled catalog is selected
- **THEN** startup applies the selected bundled catalog over stale managed
  registrations and preserves unrelated configuration.

#### Scenario: the container restarts with an unchanged catalog

- **WHEN** startup selects the catalog that is already registered
- **THEN** every client's configuration file is byte-identical afterwards.

## Rationale

### The image installs the catalog, and the create phase installs it again

The catalog is installed during the image build so a consumer that runs the
image with no volumes and no lifecycle commands resolves `agentdev:*` skills.
The Dev Container's home volume shadows everything the build wrote into a home,
so its create phase installs the catalog again.

Rejected:

- **Each raw-image consumer installing the catalog itself.** It duplicates the
  lifecycle commands' logic and leaves the image carrying a staged catalog that
  looks installed but is not.

### CI agent jobs run the lifecycle commands against their checkout

A GitHub Actions `container:` job runs no Dev Container lifecycle command, so a
job that needs `agentdev:*` skills runs the three phases itself. Running all
three, the attach phase included, makes the skill the agent uses the one on the
branch under review: a pull request that changes a skill is reviewed by the
skill as changed. An agent whose skill does not resolve improvises rather than
fails, so a missing catalog would pass a required review gate on an ungrounded
review. The create phase's `pre-commit install --install-hooks` builds an
environment for every hook, minutes of work a review job that never commits does
not need, hence `AGENTDEV_SKIP_PRE_COMMIT`; the safe-directory step is not
skippable because a CI checkout belongs to another UID. `claude-code-action`
merges its `settings` input into the user settings one level deep, so an
`enabledPlugins` in the input would replace the object the lifecycle commands
wrote; this repository's own local-scope settings would hide that loss, which
only a consumer repository shows.

Rejected:

- **Relying on the catalog installed into the image at build time.** It carries
  the image's pinned catalog version, not the branch under review.
- **An explicit workflow step that installs the catalog.** It duplicates what
  the lifecycle commands own and drifts from them.
- **Running the responder on a bare runner.** It gives up the project toolchain
  (`uv`, `bun`, the linters) that grounds a review.
- **A repository-local copy of the review skill.** It forks from the catalog's
  copy and drifts.
- **Dropping the `settings` input and relying on the user settings the lifecycle
  commands wrote.** The project's permissions and model pin reach the responder
  session only through that input.

### The runtime ships no code-graph index

The images, the runtime, and the catalog ship no code-graph daemon, MCP server,
hook, or index; agents orient with `grep` over the code and the specs. The
maintainer removed codebase-memory-mcp because agents never called it
unprompted, found the same code and passed the same tests without it, and cost
more and took longer when told to use it, while its graph missed virtual C++
dispatch and cross-package Python calls on untyped receivers. Its install
outlives the image in the home volume, where a hook naming a missing binary
fails on every tool call, so the create phase clears it; that cleanup stays
until no supported instance can still hold a CBM install.

Rejected:

- **Keeping the MCP server opt-in.** It keeps a pinned binary and its upgrades
  for a tool no run chose unprompted.
- **Requiring a manual `uninstall` before upgrading.** Anyone who misses the
  step gets a failing hook on every tool call.

### Each worktree loads its catalog from a marketplace inside the worktree

A worktree's catalog is a file-source marketplace at
`<worktree>/.claude/marketplace.local.json`, installed at local scope by the
`WorktreeCreate` hook, because that is the only form Claude Code reads in place
from the worktree, uncommitted edits included. A directory marketplace's name is
global to the user, hence the `wt-<worktree name>` rename and the ownership
check. A worktree session reads the main checkout's
`.claude/settings.local.json` and its `enabledPlugins` wins over the worktree's,
and a local-scope install run in a worktree writes there. So the hook moves its
enables into the worktree's own file, removing rather than disabling them in the
main checkout's, and every shared install runs at user scope, which a worktree
can override. The hooks live in user settings because they apply to every
session.

Rejected:

- **A generated marketplace folder under `~/.claude/`** holding a renamed
  manifest and a copy of `.agents/plugins/`. The copy is a snapshot that never
  follows the worktree's edits.
- **A renamed manifest outside the worktree pointing back into it.** Claude Code
  refuses absolute, climbing, and symlinked plugin entries and the `directory`
  and `local` source types; a `git-subdir` source with a `file://` URL clones
  the branch's last commit, so uncommitted edits never load and each commit
  needs `claude plugin update`.
- **Inline plugins** (`claude --plugin-dir`, `CLAUDE_CODE_PLUGIN_DIRS`). The
  variable is ignored in a worktree's `.claude/settings.json` and
  `.claude/settings.local.json`, and `claude remote-control` has no
  `--plugin-dir`, so no hook can turn them on per worktree.
- **A `SessionStart` reinstall.** Plugins load before `SessionStart` runs, so a
  reinstall applies only from the next session.
- **Hooks in the agentdev plugin.** A worktree session disables the shared
  plugin, so a worktree created from inside one would get no hook.
