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
- A `SubagentStart` hook. Rejected: it runs when a session dispatches a
  subagent, not when Claude Code makes a worktree.

## Consequences

- A worktree session reads `.claude/settings.local.json` of the main checkout,
  and its `enabledPlugins` overrides the worktree. A local-scope installation in
  a worktree writes there. As a result, the hook moves its `enabledPlugins`
  entries into the file of the worktree and removes them from the main checkout.
- Each shared installation runs at user scope, which a worktree can override.
- The hooks are in the user settings, because they apply to each session.
- The hook installs a catalog only when the worktree holds a complete catalog.
  In the worktree settings, it sets each plugin of the shared marketplace to
  `false`.
- The hook makes the worktree at `<repository>/.claude/worktrees/<name>` on the
  branch `worktree-<name>`, as Claude Code does without a hook.
- When a step of the hook fails, the hook removes what it made and exits
  nonzero, so no session starts in an incomplete worktree.
- `WorktreeRemove` removes `wt-<name>` before the worktree, also when the
  worktree is gone. It removes `wt-<name>` only when the file of its own
  worktree registered it, and it keeps the branch.
- The hook copies the local `permissions.allow` rules of the main checkout into
  the local settings of the worktree.
