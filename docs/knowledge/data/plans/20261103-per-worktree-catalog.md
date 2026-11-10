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

What the catalog route has to work around, on Claude Code 2.1.316:

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
hooks](../../../guides/worktree-hooks.md).

## Approach

`agentdev-runtime` gains a `worktree` subcommand with two hook entry points,
`create` and `remove`, and registers them as command hooks under
`WorktreeCreate` and `WorktreeRemove` in the user's Claude settings
(`$CLAUDE_CONFIG_DIR/settings.json`, default `~/.claude/settings.json`).

`agentdev-runtime worktree create` makes the worktree the way [Worktree
hooks](../../../guides/worktree-hooks.md) prescribes — at
`<repository>/.claude/worktrees/<name>` on a new branch `worktree-<name>` — for
any repository, and copies `permissions.allow` from the main checkout's
`.claude/settings.local.json` into the worktree's. When the new worktree ships a
complete catalog (`catalog.complete`), it also:

1. writes `<worktree>/.claude/marketplace.local.json`, the worktree's
   `.claude-plugin/marketplace.json` with `name` set to `wt-<name>`;
2. registers it with `claude plugin marketplace add` and installs every plugin
   it publishes as `<plugin>@wt-<name>` at local scope, from the worktree;
3. sets `<plugin>@<shared marketplace name>` to `false` under `enabledPlugins`
   in the worktree's `.claude/settings.local.json`, for every plugin the
   manifest publishes.

`agentdev-runtime worktree remove` uninstalls and removes the `wt-<name>`
marketplace, which also drops its entry from user settings, then removes the
worktree.

Registration happens where a checkout's own catalog is installed: the
devcontainer attach phase (`lifecycle.attached`) and the standalone runtime's
catalog step (`Workspace.catalog`), each only when the checkout ships a complete
catalog. The attach phase's install moves from local to user scope, the scope
the image-staged install and the standalone runtime already use.

Rejected alternatives:

- **A generated marketplace folder under `~/.claude/`** holding a renamed
  manifest and a copy of `.agents/plugins/`. It works, but the copy is a
  snapshot taken at creation that never follows the worktree's edits.
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

Assumptions, recorded because nothing decided them:

- Registration is idempotent and only adds; nothing unregisters the hooks when a
  later attach finds no complete catalog.
- `permissions.allow` is copied once, at creation, and merged without duplicates
  into whatever the worktree's local settings already hold.
- A worktree name that `git worktree add` refuses, or a `marketplace add` or
  `install` that fails, fails the hook: it removes what it made, prints the
  reason on stderr, and exits non-zero, so the session does not start on a
  half-made worktree.

## Implementation Steps

### Task 1: `agentdev-runtime worktree create`

**Files:** Create: `py_packages/agentdev_runtime/agentdev_runtime/worktree.py`,
`py_packages/agentdev_runtime/tests/test_worktree_create.py`; Modify:
`py_packages/agentdev_runtime/agentdev_runtime/cli.py`

- [ ] `worktree create` reads the hook's stdin JSON, resolves the repository
  from `cwd` with `git rev-parse --show-toplevel`, reduces `name` to
  `[A-Za-z0-9._-]`, runs
  `git worktree add -b worktree-<name> <repository>/.claude/worktrees/<name> HEAD`
  with git's output on stderr, and prints the worktree's absolute path as its
  only stdout line
- [ ] it merges the main checkout's `.claude/settings.local.json`
  `permissions.allow` into the worktree's `.claude/settings.local.json`, for
  every repository
- [ ] when the worktree ships a complete catalog, it writes
  `.claude/marketplace.local.json` named `wt-<name>`, registers and installs it
  at local scope from the worktree, and disables every
  `<plugin>@<shared marketplace name>` in the worktree's local settings
- [ ] a failing step removes the worktree, its branch, and any `wt-<name>`
  registration it made, and exits non-zero with the reason on stderr
- [ ] tests run the subcommand against a made-up repository and catalog, with
  `claude` replaced by a recording stub on `PATH`, covering a plain repository,
  a catalog repository, and a failing install

### Task 2: `agentdev-runtime worktree remove`

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/worktree.py`;
Create: `py_packages/agentdev_runtime/tests/test_worktree_remove.py`

- [ ] `worktree remove` reads the worktree path from the hook's stdin JSON,
  uninstalls every `<plugin>@wt-<name>` and removes the `wt-<name>` marketplace
  when one is registered, then runs `git worktree remove --force <path>`; the
  `worktree-<name>` branch stays
- [ ] a worktree that is already gone, or has no `wt-<name>` marketplace, is not
  an error
- [ ] tests run the subcommand against a worktree Task 1's subcommand made, with
  the same `claude` stub

### Task 3: Register the hooks in user settings

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/worktree.py`,
`py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py`,
`py_packages/agentdev_runtime/agentdev_runtime/workspace.py`; Create:
`py_packages/agentdev_runtime/tests/test_worktree_register.py`

- [ ] a `register` function writes one `WorktreeCreate` command hook
  (`agentdev-runtime worktree create`) and one `WorktreeRemove` command hook
  (`agentdev-runtime worktree remove`) into `$CLAUDE_CONFIG_DIR/settings.json`
  through `claude_state.update_json`, keeping every other key and every other
  hook, and adding nothing on a second run
- [ ] `lifecycle.attached` calls it when the checkout ships a complete catalog,
  and `Workspace.catalog` calls it when it selected the checkout's catalog over
  the staged one
- [ ] tests run `register` twice on a settings file holding unrelated hooks and
  keys, and run both callers with a complete and an incomplete catalog

### Task 4: Install the checkout's catalog at user scope on attach

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py`;
Create: `py_packages/agentdev_runtime/tests/test_attach_catalog_scope.py`

- [ ] `lifecycle.attached` installs a complete checkout catalog with
  `catalog.install(settings, folder, 'user')`
- [ ] a test runs the attach-phase catalog step with a recording `claude` stub
  and asserts every `marketplace add` and `plugin install` carries
  `--scope user`

### Task 5: Confirm the `WorktreeRemove` input on agent-dev3

**Files:** Modify: `docs/knowledge/data/architecture/worktree-hooks.md`

- [ ] with Tasks 1–3 installed on agent-dev3, a Remote Control spawned session's
  automatic cleanup runs `agentdev-runtime worktree remove`, and the field
  naming the worktree path in its stdin is recorded in
  `data/architecture/worktree-hooks`, replacing "not yet confirmed"

### Task 6: Prove the route end to end on agent-dev3

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

### Task 7: Record the design

**Files:** Create: `docs/knowledge/data/architecture/per-worktree-catalog.md`;
Modify: `docs/knowledge/data/architecture.md`

- [ ] `data/architecture/per-worktree-catalog` records the file-source
  marketplace inside the worktree, the user-scope install, where the hooks are
  registered, and every rejected alternative in `## Approach`, and links
  `data/architecture/worktree-hooks`; `data/architecture.md` links it

## Spec changes

[Catalog lifecycle](../../../../openspec/specs/catalog-lifecycle/spec.md):

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

When the attach lifecycle or the standalone runtime registers a checkout's own
catalog, it SHALL also register `agentdev-runtime worktree create` and
`agentdev-runtime worktree remove` as the user's Claude `WorktreeCreate` and
`WorktreeRemove` hooks. A worktree that hook creates SHALL load every plugin of
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

## Verification

- `uv run pytest py_packages/agentdev_runtime/tests/test_worktree_create.py py_packages/agentdev_runtime/tests/test_worktree_remove.py py_packages/agentdev_runtime/tests/test_worktree_register.py`
- `uv run pytest py_packages/agentdev_runtime/tests/test_attach_catalog_scope.py`
- Tasks 5 and 6 on agent-dev3, with each session's `init` event read from
  `--output-format stream-json --verbose` or the transcript.

## Out of scope

- Per-worktree catalogs for worktrees no `WorktreeCreate` hook made:
  `git worktree add`, `/agentdev:git-new-branch --worktree`, OpenCode.
- Inline plugins for a local `claude -w` session; nothing changes for them.
- A macOS host without the runtime: `bin/macos-bootstrap.zsh` installs the
  catalog at user scope and registers no hooks.
- Sessions revived by a Remote Control server in another spawn mode ([Claude
  Remote Control spawn mode
  switch](../../../../openspec/specs/claude-remote-control/spec.md#rationale)).
- Per-checkout uv environments, which [Give each checkout its own uv
  environment](20261101-per-checkout-uv-environments.md) owns.

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
- `py_packages/agentdev_runtime/agentdev_runtime/cli.py::PASSTHROUGH` —
  `PASSTHROUGH`
