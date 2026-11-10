---
type: architecture
description: Why each checkout in the Dev Container has its own uv environment on the /uv volume, reached through a .venv link, which events create and remove it, and the alternatives rejected.
sources:
- resource: .devcontainer/devcontainer.json
- resource: py_packages/agentdev_runtime/agentdev_runtime/project.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/worktree.py
- resource: .devcontainer/docker-compose.yml
---

# uv environment location

Every checkout in the Dev Container — the workspace folder and each Git worktree
— has its own uv environment at `$AGENTDEV_VENV_ROOT/<checkout directory name>`
(default `/uv/venvs`). The checkout's `.venv` is a symlink to it, and commands
reach it through `uv run`.

## Why the environment is out of tree

`UV_CACHE_DIR` (`/uv/cache`) and the environments (`/uv/venvs/...`) are on the
same mount. That is what lets uv **hardlink** packages out of its cache into an
environment.

An in-tree `.venv` would land on the workspace bind mount, a different
filesystem. Hardlinking across filesystems is impossible, so uv silently falls
back to copying every package: a slower sync and duplicated disk, with no error.
On a macOS host the bind mount is VirtioFS, and only the link crosses it, so
none of uv's file-heavy I/O does. Measured with this project's environment
(about 25,000 files, uv 0.13) on Docker Desktop for macOS:

| Operation                           | Both on `/uv` | Both on the bind mount | Cache on `/uv`, environment on the bind mount |
| ----------------------------------- | ------------- | ---------------------- | --------------------------------------------- |
| Hard links from the cache           | yes           | yes                    | no — full copy                                |
| `uv sync` into an empty environment | 0.18 s        | 11.7 s                 | 16.5 s                                        |
| Import of the heavy dependencies    | 0.21 s        | 0.34 s                 | 0.34 s                                        |
| `uv run python -c pass`             | 0.020 s       | 0.051 s                | 0.048 s                                       |
| Deleting the environment            | 0.08 s        | 4.3 s                  | 4.6 s                                         |

Hard links do work inside the bind mount, so cache and environment both in the
checkout avoid the copy; they do not avoid VirtioFS. Sustained small-file churn
there — seeding a cache, creating and deleting environments — can also stall
every process that touches the workspace, the VS Code server included, until the
container restarts.

## Why one environment per checkout

The `agentdev-uv` volume is Compose-project-scoped: each Dev Container instance
gets its own `/uv`, but every checkout inside one instance shares it. A single
shared environment breaks as soon as two checkouts use it: `uv run` repoints the
editable installs and exact-synced dependencies at the invoking checkout, so
concurrent sessions in different worktrees run each other's code.

## Why a `.venv` link rather than `UV_PROJECT_ENVIRONMENT`

uv ignores `.venv` while `UV_PROJECT_ENVIRONMENT` is set, and the variable is
one value for the whole container. A link carries the per-checkout choice inside
the checkout, so every `uv run` — from any shell, editor, or agent — finds its
own environment with no wrapper. The Dev Container therefore sets no
`UV_PROJECT_ENVIRONMENT`. uv also fails on a `.venv` link whose target does not
exist, so the target directory is created before the link.

## Which events create and remove an environment

`agentdev-runtime project link-venv [PATH]` creates the target directory and the
link. It is idempotent, repairs a link that points elsewhere under the root, and
leaves a real directory or a link outside the root in place with a warning. No
single event sees every checkout, so three call it:

| Trigger                                                      | Checkouts it covers                                                                                        |
| ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| the `link-venv` pre-commit hook at the `post-checkout` stage | `git worktree add` by OpenCode, a person, or a script                                                      |
| Claude `WorktreeCreate`, `agentdev-runtime worktree create`  | `claude -w`, Remote Control worktree spawns, `/batch`, and subagents dispatched with `isolation: worktree` |
| attach (`agentdev-runtime project sync`)                     | the workspace folder                                                                                       |

A `WorktreeCreate` hook replaces Claude Code's own worktree creation, so it
covers Claude's worktrees whether or not git's hooks would run for them:
`agentdev-runtime worktree create` makes the worktree with the default layout
from [Worktree hooks](worktree-hooks.md) and links its `.venv` before the
session starts there. The create phase registers it, and
`agentdev-runtime worktree remove`, in the user's Claude settings outside deploy
mode, before the Remote Control server starts and reads them.

Removal happens in two places:

- `agentdev-runtime worktree remove`, the `WorktreeRemove` hook, deletes the
  worktree's environment and then the worktree, keeping its `worktree-<name>`
  branch.
- Attach removes every directory under the root that no checkout in
  `git worktree list` names or links to, unless the checkout recorded beside it
  in `<name>.checkout` still links to it — the hooks live in the user's Claude
  settings, so they link worktrees of every repository in the container.
  `WorktreeRemove` fires only for worktrees a `WorktreeCreate` hook made, and
  git has no hook for `git worktree remove`.

The `post-checkout` trigger is a `link-venv` hook in `.pre-commit-config.yaml`,
and `project hooks` installs pre-commit's `post-checkout` script with the other
hook types. pre-commit is the only writer of `.git/hooks`, so a repository's own
`post-checkout` hooks run beside it. The hook does nothing where
`agentdev-runtime` is not on `PATH`. `default_stages` keeps every hook without
its own `stages` out of `post-checkout`.

## Rejected alternatives

- **One shared environment without editable installs.** Dependencies still
  diverge between branches.
- **An in-tree `.venv` with the uv cache inside the checkout**, every worktree
  under it. Hard links return, but all uv I/O runs on VirtioFS on macOS —
  roughly 65× slower installs, 1.6× slower imports, 2.5× slower `uv run`
  startup, and the stall risk above — and it clashes with a host `.venv`.
- **A per-checkout `UV_PROJECT_ENVIRONMENT`** set by a `uv` wrapper or by
  `CLAUDE_ENV_FILE`. Session-scoped and brittle.
- **`UV_LINK_MODE=symlink`.** A cache clean breaks every environment.
- **A `PreToolUse` hook.** It runs on every tool call.
- **`SessionStart` and `SubagentStart` hooks in the agentdev plugin.**
  `SessionStart` runs on every session start rather than once per worktree,
  `SubagentStart` fires on a dispatch rather than on a worktree's creation, and
  a worktree session that disables the shared plugin gets neither.
- **Sweeping every worktree from a hook** rather than targeting the one at hand.

## Consequences

- The four VS Code settings that take a filesystem path
  (`python.defaultInterpreterPath` and the three `ansible.*` paths) name
  `${workspaceFolder}/.venv/bin/...`, so each window follows its own checkout's
  link.
- Two checkouts with the same directory name share one environment.
- Claude Code keeps the worktree its `WorktreeCreate` hook made for a subagent
  and runs no `WorktreeRemove` for it, so that environment stays until the
  worktree is removed and the workspace is next attached.
- CI checkouts and host checkouts no Dev Container mounts keep uv's default
  in-tree `.venv`, and the deploy runtime, which serves one checkout, keeps a
  fixed `UV_PROJECT_ENVIRONMENT`.
- The checkout the Dev Container mounts belongs to the container: attach
  replaces a real uv environment (one with `pyvenv.cfg`) in the workspace folder
  with the link. The host and the container cannot share one `.venv`, because an
  environment carries its own platform's interpreter, and a host `uv` there
  fails on the link, so the host sets `UV_PROJECT_ENVIRONMENT` to a path of its
  own to work in that checkout. `.gitignore`, `search.exclude`, and the lint
  prunes keep covering `.venv`.
- Git on the host is unsupported in a checkout the Dev Container mounts. Its
  `.git/hooks` is shared through the bind mount and holds pre-commit's scripts,
  which run the interpreter they were installed with, `/usr/bin/python3` in the
  container. A host whose `/usr/bin/python3` cannot import `pre_commit` fails
  each hook, so a checkout or `git worktree add` there exits non-zero after it
  has already happened. Tests that run git on the host in such a checkout bypass
  the hooks with `core.hooksPath`.
- `project hooks` installs pre-commit's `post-checkout` stage in every checkout,
  so a repository's `.pre-commit-config.yaml` sets a top-level `default_stages`
  without `post-checkout`. Without it, every hook that has no `stages` and runs
  with `always_run` runs on each checkout, and a failing one, such as
  `no-commit-to-branch` on `main`, makes the checkout command exit non-zero.
  Checking out a commit whose config predates that setting runs its hooks this
  way too.
