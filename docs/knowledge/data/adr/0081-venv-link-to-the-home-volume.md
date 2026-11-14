---
type: adr
stage: accepted
description: Each checkout links its .venv to its own uv environment in the venv root on the home volume.
---

# Each checkout links .venv to its own environment on the home volume

The uv environments are in the venv root on the home volume, next to the uv
cache. As a result, uv can hardlink packages from the cache. Each checkout gets
its own environment, because `uv run` points editable installations at the
checkout that calls it. A `.venv` link in the checkout selects the environment,
so each `uv run` finds it with no wrapper.

## Considered Options

- A `.venv` directory in the checkout. Rejected: it is on the workspace bind
  mount, where uv copies files with no message and does not hardlink them. On a
  macOS host, each uv file operation then goes through VirtioFS.
- `UV_PROJECT_ENVIRONMENT`. Rejected: it has one value for the whole container,
  and uv ignores `.venv` while it is set. A value for each checkout from a `uv`
  wrapper or `CLAUDE_ENV_FILE` applies to one session only.
- One shared environment without editable installations. Rejected: the
  dependencies of branches are still different.
- `UV_LINK_MODE=symlink`. Rejected: when uv cleans its cache, each environment
  breaks.
- A `PreToolUse`, `SessionStart`, or `SubagentStart` hook. Rejected:
  `PreToolUse` runs at each tool call, `SessionStart` at each session, and
  `SubagentStart` at a dispatch, not when Claude Code makes a worktree. A
  session that disables the plugin gets no plugin hook.

## Consequences

- No single event finds each checkout, so three events make the link. The attach
  phase links the workspace folder. The `WorktreeCreate` hook links each
  worktree that Claude Code makes. The `link-venv` pre-commit hook at the
  `post-checkout` stage links a worktree that `git worktree add` makes.
- The `WorktreeRemove` hook removes the environment of its worktree. A worktree
  that Claude Code made for a subagent gets no `WorktreeRemove`, so its
  environment stays until the next attach after the worktree is removed.
- Two checkouts with the same directory name share one environment.
- The mounted checkout belongs to the container. The attach phase replaces a
  real uv environment in the workspace folder with the link. A host that works
  in the checkout sets its own `UV_PROJECT_ENVIRONMENT`, because an environment
  holds the interpreter of one platform.
- The repository does not support Git on the host in a checkout that the Dev
  Container mounts. The `.git/hooks` of the checkout holds the pre-commit
  scripts, which run the `/usr/bin/python3` of the container.
