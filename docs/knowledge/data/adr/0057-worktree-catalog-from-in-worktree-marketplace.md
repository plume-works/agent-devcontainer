---
type: adr
stage: accepted
description: The WorktreeCreate hook installs each worktree's catalog from a file-source marketplace inside the worktree, named wt-<worktree name>, at local scope.
---

# Each worktree loads its catalog from a marketplace in the worktree

The `WorktreeCreate` hook writes `<worktree>/.claude/marketplace.local.json` and
installs it at local scope. Claude Code reads only a file-source marketplace in
place from the worktree, with uncommitted edits. A marketplace name is global to
the user, so the hook names it `wt-<worktree name>` and checks its owner.

## Considered Options

- A generated marketplace folder in `~/.claude/` with a copy of
  `.agents/plugins/`. Rejected: the copy does not follow the edits in the
  worktree.
- A renamed manifest outside the worktree that points into it. Rejected: Claude
  Code refuses absolute, parent, and symlinked plugin paths. A `git-subdir`
  source clones the last commit, so uncommitted edits do not load.
- Inline plugins through `--plugin-dir` or `CLAUDE_CODE_PLUGIN_DIRS`. Rejected:
  the variable has no effect in the settings of a worktree, and
  `claude remote-control` has no `--plugin-dir`.
- A reinstall at `SessionStart`. Rejected: plugins load before `SessionStart`,
  so the reinstall applies only from the next session.
- Hooks in the agentdev plugin. Rejected: a worktree session disables the shared
  plugin, so a worktree made from one has no hook.
- A `SubagentStart` hook. Rejected: it runs when a session starts a subagent,
  not when Claude Code makes a worktree.

## Consequences

- A worktree session reads `.claude/settings.local.json` of the main checkout,
  and its `enabledPlugins` has priority over the worktree. A local-scope
  installation in a worktree writes there. As a result, the hook moves its
  `enabledPlugins` entries into the file of the worktree and removes them from
  the main checkout.
- Each shared installation runs at user scope, and the settings of a worktree
  have priority over user scope.
- A worktree session reads the catalog from the files in its worktree, not from
  the plugin cache, the copy of the plugin that Claude Code installs in the home
  directory. `/reload-skills` adds a skill that is new in the worktree,
  committed or not, and the session does not restart.
- A worktree session reads the body of a skill when the skill starts. As a
  result, a checkout of a different branch in the worktree changes the skill
  bodies that the session loads, and no reload is necessary.
