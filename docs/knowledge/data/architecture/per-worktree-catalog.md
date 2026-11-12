---
type: architecture
description: How each Claude worktree of a catalog checkout loads its own agentdev catalog live from its working tree — a file-source marketplace inside the worktree, installed by the WorktreeCreate hook — while the shared catalog stays installed at user scope, and the alternatives rejected.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/worktree.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/workspace.py
---

# Per-worktree catalog

Every Claude session in a container loads the shared catalog, the
`agent-devcontainer` marketplace registered at the main checkout. A worktree
made by `agentdev-runtime worktree create` in a checkout that ships a complete
catalog (`catalog.complete`) loads its own copy instead, read in place from the
worktree, uncommitted edits included. How the hooks are written and triggered is
recorded in [Worktree hooks](worktree-hooks.md).

## Design

- **A file-source marketplace inside the worktree.** `worktree create` writes
  `<worktree>/.claude/marketplace.local.json`: the worktree's own
  `.claude-plugin/marketplace.json` with `name` set to `wt-<worktree name>`. It
  registers that file with `claude plugin marketplace add` and installs every
  plugin it publishes as `<plugin>@wt-<name>` at local scope from the worktree.
  `.claude/.gitignore` ignores `*.local.json`, so the worktree stays clean.
- **The shared catalog is turned off per worktree.** The same hook sets every
  `<plugin>@<shared marketplace name>` to `false` under `enabledPlugins` in the
  worktree's `.claude/settings.local.json`.
- **The shared catalog installs at user scope.** The attach phase
  (`lifecycle.attached`), the image-staged install, and the standalone runtime
  (`Workspace.catalog`) all install at user scope. A local-scope install would
  write `enabledPlugins` into the main checkout's `.claude/settings.local.json`,
  which every worktree session also reads and which wins over the worktree's
  own, so no worktree could turn the shared catalog off.
- **`worktree remove` drops the marketplace first.** It removes `wt-<name>` when
  one is registered, also when the worktree is already gone, before it removes
  the worktree. A failing catalog step in `worktree create` removes what the
  hook made and exits non-zero, so no session starts on a half-made worktree.
- **Permissions follow the worktree.** `worktree create` merges the main
  checkout's local `permissions.allow` into the worktree's local settings, in
  every repository.
- **Where the hooks are registered.** In the user's Claude settings, by the Dev
  Container create phase outside deploy mode and by `Workspace.catalog` when it
  selects the checkout's catalog over the staged one.

## Host constraints

These hold for Claude Code 2.1.322. A version bump is the point at which to
recheck them.

- A directory marketplace's name is its manifest's `name`, and
  `known_marketplaces.json` holds one entry per name for the whole user, so a
  second checkout of the same catalog needs a marketplace with another name.
- A plugin entry must start with `./` and stay inside the marketplace's root;
  absolute, climbing, and symlinked entries are refused, and the `directory` and
  `local` plugin source types are unsupported.
- A single-file marketplace's root is the parent of the folder holding the file,
  so a file in `<worktree>/.claude/` resolves the manifest's `./` entries into
  the worktree. `marketplace add` declares it in user settings.
- A local-scope install records the folder it was run in as its project; the
  plugin is read in place from that folder.
- `marketplace add` and `plugin install` succeed again for a marketplace or
  plugin already registered, so a reused worktree can run them again.
- `marketplace remove` also uninstalls every plugin installed from that
  marketplace, from any folder.
- A worktree session reads the main checkout's `.claude/settings.local.json`,
  found through git, and its `enabledPlugins` wins over the worktree's.

## Rejected alternatives

- **A generated marketplace folder under `~/.claude/`** holding a renamed
  manifest and a copy of `.agents/plugins/`. The copy is a snapshot taken at
  creation that never follows the worktree's edits.
- **A renamed manifest outside the worktree pointing back into it.** Every local
  form is refused. A `git-subdir` source with a `file://` URL installs, but
  clones the branch's last commit into the plugin cache: uncommitted edits never
  load, and each commit needs `claude plugin update`.
- **Inline plugins** (`claude --plugin-dir`, `CLAUDE_CODE_PLUGIN_DIRS`). They
  read a folder live, but the variable is ignored in a worktree's
  `.claude/settings.json` and `.claude/settings.local.json`, and
  `claude remote-control` has no `--plugin-dir`, so no hook can turn them on per
  worktree. They stay a manual option for a local `claude -w` session.
- **A `SessionStart` reinstall.** Plugins load before `SessionStart` runs, so a
  reinstall applies only from the next session.
- **Hooks in the agentdev plugin.** A worktree session disables the shared
  plugin, so a worktree created from inside one would get no hook; user settings
  apply to every session.
