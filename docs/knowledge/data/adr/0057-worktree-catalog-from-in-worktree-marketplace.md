---
type: adr
stage: accepted
description: The WorktreeCreate hook installs each worktree's catalog from a file-source marketplace inside the worktree, named wt-<worktree name>, at local scope.
---

# Each worktree loads its catalog from a marketplace in the worktree

The `WorktreeCreate` hook writes `<worktree>/.claude/marketplace.local.json` and
installs it at local scope, because a file-source marketplace is the only form
Claude Code reads in place from the worktree, uncommitted edits included. A
marketplace name is global to the user, so the hook names it
`wt-<worktree name>` and checks its owner.

## Considered Options

- A generated marketplace folder in `~/.claude/` with a copy of
  `.agents/plugins/`. Rejected: the copy is a snapshot that never follows the
  edits in the worktree.
- A renamed manifest outside the worktree that points into it. Rejected: Claude
  Code refuses absolute, climbing, and symlinked plugin entries and the
  `directory` and `local` source types. A `git-subdir` source with a `file://`
  URL clones the last commit of the branch, so uncommitted edits never load and
  each commit needs `claude plugin update`.
- Inline plugins through `--plugin-dir` or `CLAUDE_CODE_PLUGIN_DIRS`. Rejected:
  the variable is ignored in the `.claude/settings.json` and
  `.claude/settings.local.json` of a worktree, and `claude remote-control` has
  no `--plugin-dir`, so no hook can turn them on per worktree.
- A reinstall at `SessionStart`. Rejected: plugins load before `SessionStart`,
  so the reinstall applies only from the next session.
- Hooks in the agentdev plugin. Rejected: a worktree session disables the shared
  plugin, so a worktree made from one has no hook.
- A `SubagentStart` hook. Rejected: it runs when a session starts a subagent,
  not when Claude Code makes a worktree.

## Consequences

- A worktree session reads `.claude/settings.local.json` of the main checkout,
  and its `enabledPlugins` wins over the worktree's. A local-scope installation
  in a worktree writes there. As a result, the hook moves its `enabledPlugins`
  entries into the file of the worktree and removes them from the main checkout,
  rather than set them to `false` there, because a `false` in the main checkout
  would win in the worktree too.
- Each shared installation runs at user scope, which the settings of a worktree
  override. A local-scope shared installation would write into the main
  checkout's file, and no worktree could turn the shared catalog off.
- A worktree session reads the catalog from the files in its worktree, not from
  the plugin cache, the copy of the plugin that Claude Code installs in the home
  directory. `/reload-skills` adds a skill that is new in the worktree,
  committed or not, and the session does not restart.
- A worktree session reads the body of a skill when the skill starts. As a
  result, a checkout of a different branch in the worktree changes the skill
  bodies that the session loads, and no reload is necessary.
