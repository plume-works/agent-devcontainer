---
type: architecture
description: Why the uv environment lives out of tree on the /uv volume at a fixed path, rather than as an in-tree .venv or a symlink to one.
sources:
- resource: .devcontainer/devcontainer.json
- resource: py_packages/agentdev_runtime/agentdev_runtime/project.py
- resource: .devcontainer/docker-compose.yml
---

# uv environment location

The devcontainer's Python environment lives at `/uv/venvs/ws-project`, outside
the workspace, and is reached exclusively through `uv run`. Nothing links it
back into the tree.

## Why the environment is out of tree

`UV_CACHE_DIR` (`/uv/cache`) and the environment (`/uv/venvs/...`) are on the
same mount — `/dev/vda1 /uv`. That is what lets uv **hardlink** packages out of
its cache into the environment.

An in-tree `.venv` would land on the workspace bind mount, a different
filesystem. Hardlinking across filesystems is impossible, so uv silently falls
back to copying every package. The failure mode is not an error — it is a slower
sync and duplicated disk, which is why it is worth recording rather than
rediscovering.

On Docker Desktop for macOS the workspace bind mount is VirtioFS, and every file
operation on it crosses to the host. Measured with this project's environment
(about 25,000 files, uv 0.13), against cache and environment both on `/uv`
(ext4):

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

## Why the path is a fixed string

The `agentdev-uv` volume is declared in `devcontainer.json`'s `mounts`, not
pinned to a literal name in `docker-compose.yml`. Only `agentdev-agents-auth` is
pinned that way, deliberately, so that auth state is shared across every
devcontainer instance.

Everything unpinned is Compose-project-scoped: each devcontainer instance —
worktree, Codespace, or clone — gets its **own** `/uv`. There is therefore
nothing to disambiguate inside it, and the path can be the constant
`/uv/venvs/ws-project` instead of a `${localWorkspaceFolderBasename}` template.

This matters because the path is spelled out in five places
(`UV_PROJECT_ENVIRONMENT` plus four VS Code settings that need a filesystem path
rather than a command). A constant is cheap to repeat; a templated convention
that must stay in sync across five call sites is not.

## Rejected alternatives

**Move the environment in-tree (`.venv`).** Simpler to explain and matches the
convention most Python tooling expects. Rejected: it breaks cache-to-environment
hardlinking, as above.

**Move the uv cache into the checkout too, with every worktree under it.** Puts
cache and environments on one filesystem again, so hard links return. Rejected:
all uv I/O then runs on VirtioFS — roughly 65× slower installs, 1.6× slower
imports, 2.5× slower `uv run` startup, and the stall risk above. It also does
not fix [worktrees sharing one
environment](../bugs/shared-uv-environment-across-worktrees.md) on its own: a
fixed `UV_PROJECT_ENVIRONMENT` still sends every checkout to the same path,
wherever the cache lives.

**Keep the `.venv` symlink to the out-of-tree environment.** This was the prior
state — the environment lived on `/uv`, and the project sync step recreated
`.venv` as a symlink to it on every postCreate and postAttach, as a shim for
tooling expecting the conventional path. Rejected: the repository's stated
convention is to run project commands through `uv run`, and the symlink was the
one affordance contradicting it. Once every consumer routes through `uv run` or
an absolute path, the shim has no remaining benefit and two costs — a second
name for one environment, and a stale link whenever the target path changes.

## Consequences

- Commands reach the environment through `uv run`; a bare `ruff` or `pytest`
  resolves only if the VS Code Python extension has injected the environment's
  `bin/` into the terminal's PATH.
- The four VS Code settings that take a filesystem path
  (`python.defaultInterpreterPath` and the three `ansible.*` paths) hardcode
  `/uv/venvs/ws-project/...`. Changing the environment path means changing them
  together.
- A real `.venv` in the workspace is still expected outside the devcontainer:
  host checkouts and CI (`.github/actions/setup-python-venv`) get their own
  in-tree environment, because `UV_PROJECT_ENVIRONMENT` is unset there and uv
  falls back to its default location. `.gitignore`, `search.exclude`, and the
  lint prunes keep covering it. CI no longer *activates* that environment — the
  setup action provisions it and callers use `uv run` — so the invocation
  contract is the same in both places even though the location is not.
- `agentdev-runtime project sync` carries a narrow migration cleanup that
  removes `.venv` only when it is a symlink **and** its target is under
  `/uv/venvs/` — the shape earlier revisions created with
  `ln -s "$UV_PROJECT_ENVIRONMENT" .venv`. A real directory, or a link a
  developer deliberately pointed somewhere else, is reported and left in place.
  The prefix is matched rather than the current `UV_PROJECT_ENVIRONMENT` because
  stale links predate the path change and still carry the old per-workspace
  basename. It is removable once every active worktree has re-synced.
