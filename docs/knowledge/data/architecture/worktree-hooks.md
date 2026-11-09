---
type: architecture
description: How to write Claude Code WorktreeCreate and WorktreeRemove hook overrides that create and remove git worktrees — what triggers them, what they receive, what they must return, and how the default layout looks.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/remote_control.py
---

# Worktree hooks

Claude Code creates a session's worktree itself unless a `WorktreeCreate` hook
is configured; then the hook creates it, and Claude Code only uses the folder
the hook names. `WorktreeRemove` is the matching override for removal. A
repository that needs anything done when a worktree is made — or undone when it
goes — does it in these two hooks.

## Host behavior

These hold for Claude Code 2.1.319. A version bump is the point at which to
recheck them.

- **What triggers them.** `claude -w` / `--worktree [name]`,
  `claude remote-control --spawn worktree` for every session it spawns or
  revives, `/batch`, and a subagent dispatched with `isolation: worktree`. With
  a `WorktreeCreate` hook configured, Remote Control's worktree mode also works
  in a folder that is not a git repository.
- **Remote Control reads the hooks when its server starts.** A server started
  before a hook was registered keeps creating and removing worktrees itself
  until it restarts.
- **Configuration.** Under `hooks` in a settings file, like any other hook
  event. A hook in a workspace that is not trusted does not run.
- **`WorktreeCreate` replaces creation.** Claude Code makes no worktree of its
  own. The hook receives JSON on stdin with `session_id`, `transcript_path`,
  `cwd`, `hook_event_name`, and `name`; a Remote Control spawn also sends
  `scratchpad_dir`. `cwd` is the folder the session was started from, and `name`
  is the requested worktree name — for a Remote Control spawn,
  `bridge-cse_<session id>`, and for a subagent, `agent-<agent id>`. A
  subagent's `cwd` is its parent session's folder, so a subagent of a worktree
  session gets a worktree nested in that worktree.
- **The hook returns the worktree's absolute path.** A command hook prints it on
  stdout; an HTTP or callback hook returns it as
  `hookSpecificOutput.worktreePath`. A hook that succeeds without a path fails
  the creation, and the session does not start. Anything else the hook prints —
  `git` progress included — goes to stderr.
- **The session starts in the returned folder.** Claude Code reads that
  worktree's own `.claude/settings.json` and `.claude/settings.local.json`, and
  also the main checkout's `.claude/settings.local.json`, whose values can win
  over the worktree's.
- **`WorktreeRemove` runs when Claude Code removes a worktree**, including
  Remote Control's automatic cleanup of a spawned session's worktree. Archiving
  a Remote Control session does not remove its worktree and does not run the
  hook. Its stdin carries a single field, `worktree_path`. Claude Code keeps the
  worktree a `WorktreeCreate` hook made for a subagent and runs no
  `WorktreeRemove` for it; without a hook, it removes a subagent's unchanged
  worktree itself.

## Writing the hooks

Match the layout Claude Code uses without a hook, so sessions and tools that
expect it keep working:

| Item     | Default                                     |
| -------- | ------------------------------------------- |
| Location | `<repository>/.claude/worktrees/<name>`     |
| Branch   | `worktree-<name>`, created for the worktree |

`WorktreeCreate`:

1. Read the stdin JSON. Resolve the repository from `cwd` with
   `git -C <cwd> rev-parse --show-toplevel`, so a session started in a subfolder
   still lands at the repository root.
2. Reduce `name` to characters that are safe in a path and a branch name.
3. Run
   `git -C <repository> worktree add -b worktree-<name> <repository>/.claude/worktrees/<name> <base>`,
   with its output sent to stderr.
4. Do the repository's own setup inside the new worktree.
5. Print the worktree's absolute path as the only stdout line, and exit `0`.

Exit non-zero, with the reason on stderr, when any step fails; a half-made
worktree is the hook's to remove before it exits.

`WorktreeRemove`:

1. Read the stdin JSON and resolve the worktree path from it.
2. Undo the repository's own setup for that worktree.
3. Run `git worktree remove --force <path>`. Deleting the `worktree-<name>`
   branch is the hook's choice; a branch with unpushed commits is work the user
   may still want.

Both hooks run once per worktree and must not assume they are the only session
on the machine: anything they write outside the worktree is shared with every
other session.

## Rejected alternatives

- **`SessionStart`.** It runs on every session start, not once per worktree, and
  after the session has already loaded its settings and plugins.
- **`SubagentStart`.** It fires when a session dispatches a subagent, not when a
  worktree is created.
