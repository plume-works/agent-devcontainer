---
type: plan
created: 2026-11-03
release: internal
description: Give every worktree Claude Code creates in a catalog checkout its own agentdev catalog, read live from the worktree, through WorktreeCreate and WorktreeRemove hooks that agentdev-runtime provides and registers, and move the attach-phase catalog install to user scope so worktree settings can turn the shared catalog off.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/catalog.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/workspace.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/claude_state.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/cli.py
- resource: https://code.claude.com/docs/en/hooks
rank: 400
---

# Give each Claude worktree its own agentdev catalog

## Context

The agentdev catalog is one directory marketplace, `agent-devcontainer`,
registered at the main checkout. Every Claude session in the container —
sessions in `.claude/worktrees/*` included — loads `agentdev` and `self-improve`
from the main checkout's `.agents/plugins/`. A worktree session working on a
catalog change therefore runs the main checkout's skills and agents, not its
own, and a main checkout that falls behind `origin/main` serves stale skills to
every session in the container.

The catalog route rests on these Claude Code constraints (checked against Claude
Code 2.1.316):

- A directory marketplace's name is the `name` field of its
  `.claude-plugin/marketplace.json`; the `extraKnownMarketplaces` key does not
  rename it. `~/.claude/plugins/known_marketplaces.json` holds one entry per
  name for the whole user, so a second checkout of the same catalog needs a
  marketplace with a different name.
- A marketplace's plugin entry must start with `./` and stay inside the
  marketplace's root; absolute, climbing, and symlinked entries are refused, and
  the `directory` and `local` plugin source types are unsupported.
- A marketplace can be a single JSON file:
  `claude plugin marketplace add <file>.json` registers source
  `{"source": "file", "path": "<file>.json"}`, and its root — against which `./`
  entries resolve — is the parent of the folder holding the file. A file at
  `<worktree>/.claude/marketplace.local.json` has the worktree as its root, so
  the manifest's unchanged `./.agents/plugins/<plugin>` entries resolve into the
  worktree. A plugin installed from it at local scope is read in place from
  `<worktree>/.agents/plugins/<plugin>`, uncommitted changes included.
  `marketplace add` declares the marketplace in user settings.
- `.claude/.gitignore` ignores `*.local.json`, so that file leaves the worktree
  clean.
- A worktree session reads the main checkout's `.claude/settings.local.json` as
  well as its own, and the main checkout's `enabledPlugins` wins over the
  worktree's. The main checkout is found through git, not the folder layout. The
  devcontainer's attach phase installs this checkout's catalog at local scope
  (`lifecycle.attached` → `catalog.install(settings, folder, None)`), which
  writes the shared catalog's `enabledPlugins` into exactly that file, so no
  worktree can turn the shared catalog off while it does.
- With the shared catalog enabled at user scope and disabled in a worktree's
  local settings, a worktree session loads only its own copy and a main-checkout
  session still loads the shared one.

How to write the hooks themselves — triggers, stdin, the returned path, the
default layout — is recorded in [Worktree
hooks](../architecture/worktree-hooks.md).

## Approach

[Give each checkout its own uv
environment](20261101-per-checkout-uv-environments.md) provides
`agentdev-runtime worktree create` and `worktree remove` as the user's Claude
`WorktreeCreate` and `WorktreeRemove` hooks (`$CLAUDE_CONFIG_DIR/settings.json`,
default `~/.claude/settings.json`), and registers them in every Dev Container's
create phase outside deploy mode. `worktree create` makes the worktree the way
[Worktree hooks](../architecture/worktree-hooks.md) prescribes — at
`<repository>/.claude/worktrees/<name>` on a new branch `worktree-<name>` — and
links its uv environment. This plan adds its catalog steps inside those two
subcommands.

`agentdev-runtime worktree create` also copies `permissions.allow` from the main
checkout's `.claude/settings.local.json` into the worktree's, for any
repository. When the new worktree ships a complete catalog (`catalog.complete`),
it also:

1. writes `<worktree>/.claude/marketplace.local.json`, the worktree's
   `.claude-plugin/marketplace.json` with `name` set to `wt-<name>`;
2. registers it with `claude plugin marketplace add` and installs every plugin
   it publishes as `<plugin>@wt-<name>` at local scope, from the worktree;
3. sets `<plugin>@<shared marketplace name>` to `false` under `enabledPlugins`
   in the worktree's `.claude/settings.local.json`, for every plugin the
   manifest publishes.

`agentdev-runtime worktree remove` uninstalls and removes the `wt-<name>`
marketplace, which also drops its entry from user settings, before it removes
the worktree.

The standalone runtime's catalog step (`Workspace.catalog`) also registers the
hooks, through the same `worktree.register`, when it selects the checkout's
catalog over the staged one. The attach phase's install moves from local to user
scope, the scope the image-staged install and the standalone runtime already
use.

Rejected alternatives:

- **A generated marketplace folder under `~/.claude/`** holding a renamed
  manifest and a copy of `.agents/plugins/`. Its copy is a snapshot taken at
  creation that never follows the worktree's edits.
- **A renamed manifest outside the worktree pointing back into it.** Every local
  form is refused (see `## Context`). A `git-subdir` source with a `file://` URL
  installs, but clones the branch's last commit into the plugin cache:
  uncommitted edits never load, and each commit needs `claude plugin update`.
- **Inline plugins** (`claude --plugin-dir`, `CLAUDE_CODE_PLUGIN_DIRS`). They
  read a folder live and replace the installed plugin of the same name, but the
  variable is ignored in a worktree's `.claude/settings.json` and
  `.claude/settings.local.json`, and `claude remote-control` has no
  `--plugin-dir`, so no hook can turn them on per worktree. They stay a manual
  option for a local `claude -w` session.
- **A `SessionStart` reinstall.** Plugins load before `SessionStart` runs, so a
  reinstall applies only from the next session.
- **Hooks in the agentdev plugin.** A worktree session disables the shared
  plugin, so a worktree created from inside one would get no hook; user settings
  apply to every session.

Assumptions:

- `permissions.allow` is copied once, at creation, and merged without duplicates
  into whatever the worktree's local settings already hold.
- A `marketplace add` or `install` that fails fails the hook: it removes what it
  made, prints the reason on stderr, and exits non-zero, so the session does not
  start on a half-made worktree.

## Implementation Steps

### Task 1: Add the catalog steps to `agentdev-runtime worktree create`

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/worktree.py`;
Create: `py_packages/agentdev_runtime/tests/test_worktree_catalog_create.py`

- [x] `worktree create` merges the main checkout's `.claude/settings.local.json`
  `permissions.allow` into the worktree's `.claude/settings.local.json`, for
  every repository
  - **Evidence:**
    `py_packages/agentdev_runtime/tests/test_worktree_catalog_create.py::test_a_plain_repository_gets_permissions_and_no_marketplace`
    and `::test_permissions_merge_without_duplicates`
- [x] when the worktree ships a complete catalog, it writes
  `.claude/marketplace.local.json` named `wt-<name>`, registers and installs it
  at local scope from the worktree, and disables every
  `<plugin>@<shared marketplace name>` in the worktree's local settings
  - **Evidence:**
    `py_packages/agentdev_runtime/tests/test_worktree_catalog_create.py::test_a_catalog_repository_installs_its_own_catalog`
- [x] a failing catalog step removes the worktree, its branch, and any
  `wt-<name>` registration it made, and exits non-zero with the reason on stderr
  - **Evidence:**
    `py_packages/agentdev_runtime/tests/test_worktree_catalog_create.py::test_a_failing_install_removes_the_worktree_and_registration`
- [x] tests run the subcommand against a made-up repository and catalog, with
  `claude` replaced by a recording stub on `PATH`, covering a plain repository,
  a catalog repository, and a failing install
  - **Evidence:**
    `uv run pytest py_packages/agentdev_runtime/tests/test_worktree_catalog_create.py`

### Task 2: Add the catalog step to `agentdev-runtime worktree remove`

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/worktree.py`;
Create: `py_packages/agentdev_runtime/tests/test_worktree_catalog_remove.py`

- [x] `worktree remove` uninstalls every `<plugin>@wt-<name>` and removes the
  `wt-<name>` marketplace when one is registered, before it removes the
  worktree, and also when the worktree is already gone
  - **Evidence:**
    `py_packages/agentdev_runtime/tests/test_worktree_catalog_remove.py::test_removing_a_worktree_removes_its_marketplace_first`
    and `::test_a_gone_worktree_still_loses_its_marketplace`
- [x] a worktree with no `wt-<name>` marketplace is not an error
  - **Evidence:**
    `py_packages/agentdev_runtime/tests/test_worktree_catalog_remove.py::test_a_worktree_without_a_marketplace_is_removed`
- [x] tests run the subcommand against a worktree Task 1's subcommand made, with
  the same `claude` stub
  - **Evidence:**
    `uv run pytest py_packages/agentdev_runtime/tests/test_worktree_catalog_remove.py`

### Task 3: Register the hooks from the standalone runtime

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/workspace.py`;
Create: `py_packages/agentdev_runtime/tests/test_workspace_worktree_register.py`

- [x] `Workspace.catalog` calls `worktree.register` when it selected the
  checkout's catalog over the staged one
  - **Evidence:**
    `py_packages/agentdev_runtime/tests/test_workspace_worktree_register.py::test_a_complete_checkout_catalog_registers_the_hooks`
- [x] tests run `Workspace.catalog` with a complete and an incomplete catalog
  - **Evidence:**
    `uv run pytest py_packages/agentdev_runtime/tests/test_workspace_worktree_register.py`

### Task 4: Install the checkout's catalog at user scope on attach

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py`;
Create: `py_packages/agentdev_runtime/tests/test_attach_catalog_scope.py`

- [x] `lifecycle.attached` installs a complete checkout catalog with
  `catalog.install(settings, folder, 'user')`
  - **Evidence:**
    `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py::attached` ›
    "catalog.install(settings, folder, 'user')"
- [x] a test runs the attach-phase catalog step with a recording `claude` stub
  and asserts every `marketplace add` and `plugin install` carries
  `--scope user`
  - **Evidence:**
    `py_packages/agentdev_runtime/tests/test_attach_catalog_scope.py::test_attach_installs_the_checkout_catalog_at_user_scope`

### Task 5: Prove the route end to end on agent-dev3

**Files:** none

- [ ] once the runtime on agent-dev3 has registered the hooks, a session spawned
  from claude.ai through Remote Control in `worktree` mode lists one `agentdev`
  in its `init` event, source `agentdev@wt-<name>`, path
  `<worktree>/.agents/plugins/agentdev`, and loads a skill added uncommitted in
  that worktree; a session in the main checkout lists
  `agentdev@agent-devcontainer`
- [ ] after Remote Control's cleanup of that session, `~/.claude/settings.json`,
  `~/.claude/plugins/known_marketplaces.json`, and
  `~/.claude/plugins/installed_plugins.json` hold no `wt-<name>` entry, and
  `git worktree list` no longer shows the worktree

### Task 6: Record the design

**Files:** Create: `docs/knowledge/data/architecture/per-worktree-catalog.md`;
Modify: `docs/knowledge/data/architecture.md`

- [ ] `data/architecture/per-worktree-catalog` records the file-source
  marketplace inside the worktree, the user-scope install, where the hooks are
  registered, and every rejected alternative in `## Approach`, and links
  `data/architecture/worktree-hooks`; `data/architecture.md` links it

## Spec changes

[Catalog lifecycle](../spec/catalog-lifecycle.md):

``` markdown
## MODIFIED Requirements

### Requirement: this repository's own checkout overrides the staged catalog on attach

The attach lifecycle SHALL register this checkout's complete Claude and OpenCode
catalog over the staged copy, installing the Claude catalog at user scope, and
SHALL leave the staged copy selected when the mounted repository does not
contain a complete catalog. A complete catalog SHALL consist of
`.claude-plugin/marketplace.json` and the OpenCode bridge directory.

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

#### Scenario: the attach install leaves the main checkout's local settings alone

- **WHEN** attach registers a complete checkout catalog
- **THEN** the catalog's plugins are enabled in the user's Claude settings and
  no `enabledPlugins` entry is written to the checkout's
  `.claude/settings.local.json`.

## ADDED Requirements

### Requirement: each Claude worktree of a catalog checkout loads its own catalog

When the standalone runtime registers a checkout's own catalog, it SHALL also
register `agentdev-runtime worktree create` and
`agentdev-runtime worktree remove` as the user's Claude `WorktreeCreate` and
`WorktreeRemove` hooks, as the Dev Container create phase does outside deploy mode. A worktree that
hook creates in a checkout that ships a complete catalog SHALL load every plugin of
its own checkout's catalog from the worktree's working tree, under a marketplace
named `wt-<worktree name>`, and SHALL NOT load the shared catalog's plugins.

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
```

## Depends on

[Give each checkout its own uv
environment](20261101-per-checkout-uv-environments.md)

## Verification

- `uv run pytest py_packages/agentdev_runtime/tests/test_worktree_catalog_create.py py_packages/agentdev_runtime/tests/test_worktree_catalog_remove.py py_packages/agentdev_runtime/tests/test_workspace_worktree_register.py`
- `uv run pytest py_packages/agentdev_runtime/tests/test_attach_catalog_scope.py`
- Task 5 on agent-dev3, with each session's `init` event read from
  `--output-format stream-json --verbose` or the transcript.

## Out of scope

- Per-worktree catalogs for worktrees no `WorktreeCreate` hook made:
  `git worktree add`, `/agentdev:git-new-branch --worktree`, OpenCode.
- Inline plugins for a local `claude -w` session; nothing changes for them.
- A macOS host without the runtime: `bin/macos-bootstrap.zsh` installs the
  catalog at user scope and registers no hooks.
- Sessions revived by a Remote Control server in another spawn mode ([Claude
  Remote Control spawn mode
  switch](../architecture/claude-remote-control-spawn-mode-switch.md)).

## Key references

- `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py::attached` —
  `attached`
- `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py::attached` —
  `catalog.install(settings, folder, None)`
- `py_packages/agentdev_runtime/agentdev_runtime/catalog.py::complete` —
  `complete`
- `py_packages/agentdev_runtime/agentdev_runtime/catalog.py::claude` — `claude`
- `py_packages/agentdev_runtime/agentdev_runtime/catalog.py::install` —
  `install`
- `py_packages/agentdev_runtime/agentdev_runtime/workspace.py::Workspace.select_catalog`
  — `Workspace.select_catalog`
- `py_packages/agentdev_runtime/agentdev_runtime/workspace.py::Workspace.catalog`
  — `Workspace.catalog`
- `py_packages/agentdev_runtime/agentdev_runtime/claude_state.py::update_json` —
  `update_json`
- `py_packages/agentdev_runtime/agentdev_runtime/remote_control.py::config_dir`
  — `config_dir`
- `py_packages/agentdev_runtime/agentdev_runtime/worktree.py::create` —
  `create`, which this plan's catalog steps extend
- `py_packages/agentdev_runtime/agentdev_runtime/worktree.py::remove` — `remove`
- `py_packages/agentdev_runtime/agentdev_runtime/worktree.py::register` —
  `register`
