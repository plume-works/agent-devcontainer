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
so each `uv run` finds it with no wrapper
(`py_packages/agentdev_runtime/agentdev_runtime/project.py::link_venv`).

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
- The attach phase then removes each environment in the venv root that no
  checkout uses
  (`py_packages/agentdev_runtime/agentdev_runtime/project.py::prune_venvs`). It
  keeps an environment when the checkout that `<name>.checkout` records still
  links to it, because the hooks link the worktrees of each repository in the
  container.
- The `WorktreeRemove` hook removes the environment of its worktree. A worktree
  that Claude Code made for a subagent gets no `WorktreeRemove`, so its
  environment stays until the next attach after the worktree is removed.
- `link_venv` makes the target directory before the link, because uv fails on a
  `.venv` link to a directory that does not exist. It does not change a real
  `.venv` directory or a link outside the venv root. It does nothing when the
  parent of the venv root does not exist, so it does not change a checkout
  outside a Dev Container.
- Two checkouts with the same directory name share one environment.
- The deploy runtime serves one checkout and keeps a fixed
  `UV_PROJECT_ENVIRONMENT`. CI checkouts and host checkouts that no Dev
  Container mounts keep the default `.venv` of uv in the checkout.
- `project hooks` installs the `post-checkout` stage of pre-commit in each
  checkout. As a result, `.pre-commit-config.yaml` sets a `default_stages`
  without `post-checkout`, so that a hook with no `stages` does not run at each
  checkout.
- The mounted checkout belongs to the container. The attach phase replaces a
  real uv environment in the workspace folder with the link. A host that works
  in the checkout sets its own `UV_PROJECT_ENVIRONMENT`, because an environment
  holds the interpreter of one platform.
- The repository does not support Git on the host in a checkout that the Dev
  Container mounts. The `.git/hooks` of the checkout holds the pre-commit
  scripts, which run the `/usr/bin/python3` of the container.
