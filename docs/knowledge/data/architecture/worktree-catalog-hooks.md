---
type: architecture
description: How a Claude Code worktree gets its own copy of the agentdev catalog through WorktreeCreate and WorktreeRemove hook overrides — what the hooks must do, the host constraints that shape them, and the alternatives that fail.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-03T07:45:32Z
sources:
- resource: .claude-plugin/marketplace.json
- resource: .claude/settings.json
- resource: py_packages/agentdev_runtime/agentdev_runtime/remote_control.py
---

# Worktree catalog hooks

The catalog is registered as one directory marketplace, `agent-devcontainer`,
pointing at the main checkout. Every Claude Code session on the machine,
including one in a worktree, loads `agentdev` and `self-improve` from there, so
a worktree runs the main checkout's catalog rather than its own branch's, and a
stale main checkout serves stale skills to every session.

The decision (human:author) is to give each worktree its own catalog through
`WorktreeCreate` and `WorktreeRemove` hooks configured in user settings.

## Host behavior

These hold for Claude Code 2.1.316. A version bump is the point at which to
recheck them.

- **A marketplace's name is the `name` field of its
  `.claude-plugin/marketplace.json`.** The key under `extraKnownMarketplaces` is
  ignored for a directory source, and `claude plugin marketplace add` takes no
  name. Declaring a worktree path under a new key re-points the existing
  `agent-devcontainer` entry instead, which switches every session on the
  machine to that worktree's catalog.
- **The marketplace registry is per user, not per project.**
  `~/.claude/plugins/known_marketplaces.json` holds one entry per name; plugin
  installs are recorded per project path in `installed_plugins.json`.
- **A marketplace entry may not leave the marketplace folder.** An install
  refuses an entry that is absolute, climbs out, or traverses a symlink, so a
  generated marketplace has to hold real copies of the plugin trees.
- **`WorktreeCreate` replaces worktree creation.** The hook receives
  `session_id`, `transcript_path`, `cwd`, `hook_event_name`, and `name` on
  stdin, must create the worktree itself, and prints its absolute path on
  stdout. A hook that succeeds without printing a path fails the creation.
- **`claude remote-control --spawn worktree` creates worktrees through the same
  path.** It accepts a machine with no git repository when `WorktreeCreate`
  hooks are configured, and a spawned session starts in the folder the hook
  printed. Remote Control's automatic cleanup of a spawned session's worktree
  runs `WorktreeRemove`.
- **A worktree session reads the main checkout's `.claude/settings.local.json`
  as well as its own**, and an `enabledPlugins` value there wins over the
  worktree's local settings. The worktree's local settings do override user
  settings.

## The hooks

`WorktreeCreate`:

1. Creates the worktree at `<repo>/.claude/worktrees/<name>` on branch
   `worktree-<name>`, the layout Claude Code uses without a hook.
2. Copies the worktree's `.claude-plugin/marketplace.json` and
   `.agents/plugins/` into `~/.claude/wt-marketplaces/wt-<name>/`, with the
   manifest's `name` set to `wt-<name>`.
3. Writes the worktree's `.claude/settings.local.json` from the main checkout's:
   every `<plugin>@agent-devcontainer` set to `false`, every
   `<plugin>@wt-<name>` set to `true`, `extraKnownMarketplaces` holding only
   `wt-<name>`, and `permissions.allow` gaining `Bash(*)` and
   `Bash(/root/.claude/plugins/cache/wt-<name>/agentdev/*)`. The second rule
   replaces the cache rule in `.claude/settings.json`, whose path names the
   `agent-devcontainer` marketplace.
4. Prints the worktree path.

`WorktreeRemove` runs `claude plugin marketplace remove wt-<name>`, deletes
`~/.claude/wt-marketplaces/wt-<name>/`, and removes the worktree.

Because the main checkout's local settings win in a worktree, the shared
catalog's `enabledPlugins` live in user settings (`~/.claude/settings.json`),
and the main checkout's `settings.local.json` carries none. A worktree's local
`false` then switches the shared catalog off.

## Consequences

- A worktree runs the catalog of the commit it was created from, copied at
  creation. Catalog edits made in the worktree afterwards are not loaded until
  the copy is refreshed.
- Each worktree adds one marketplace entry and one plugin cache folder per user,
  removed only by `WorktreeRemove`. A worktree deleted any other way leaves them
  behind.
- A session in the main checkout is unaffected: it still loads the catalog from
  `/workspaces/agent-devcontainer`.

## Rejected alternatives

- **A new key under `extraKnownMarketplaces` in the worktree's local settings.**
  The key is ignored, and the entry hijacks the shared marketplace for every
  session.
- **A generated manifest whose plugin folders are symlinks into the worktree.**
  The install refuses link-traversing entries.
- **Renaming the marketplace inside the worktree's own `marketplace.json`.** It
  leaves a change to a tracked file in every worktree, and any merge that
  touches the file conflicts.
- **`claude --plugin-dir` per session.** It is a command-line flag, and Remote
  Control spawns its sessions without one.
- **Reinstalling from a `SessionStart` hook.** The registry is shared, so a
  reinstall that re-points it changes the catalog of every running session, and
  it applies only from the next session.
- **`SubagentStart`.** It fires when a session dispatches a subagent, not when a
  worktree is created.
