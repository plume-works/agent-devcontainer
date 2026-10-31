---
type: architecture
description: Why each checkout keeps its own in-tree .venv, rather than every checkout in a devcontainer sharing one environment at a fixed path on the /uv volume.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T21:10:00Z
sources:
- resource: .devcontainer/devcontainer.json
- resource: py_packages/agentdev_runtime/agentdev_runtime/project.py
- resource: .devcontainer/docker-compose.yml
---

# uv environment location

Each checkout's Python environment is its own in-tree `.venv`, uv's default.
`UV_PROJECT_ENVIRONMENT` is unset in the devcontainer, as it is on a host or a
CI runner, and the environment is reached through `uv run`.

## Why each checkout owns its environment

The project installs its own packages (`agentdev_runtime`,
`validate_agent_files`) as editable installs, and `uv run` repoints them at the
checkout that invokes it. One environment shared by several checkouts therefore
serves whichever checkout synced last. Git worktrees in one devcontainer, such
as the `.claude/worktrees/` checkouts concurrent agent sessions use, are several
checkouts on one `/uv` volume: with a shared environment, a session's tests and
tools run another worktree's code ([Bug: worktrees in one devcontainer share the
uv environment](../bugs/shared-uv-environment-across-worktrees.md)).

## Consequences

- The cache stays on the `/uv` volume (`UV_CACHE_DIR`), shared by every
  checkout. The `.venv` is on the workspace bind mount, a different filesystem,
  so uv cannot hardlink from the cache and copies instead; `UV_LINK_MODE=copy`
  states that, so uv does not warn on every sync. Each checkout pays one full
  sync and its own disk.
- The four VS Code settings that take a filesystem path
  (`python.defaultInterpreterPath` and the three `ansible.*` paths) name
  `${workspaceFolder}/.venv/bin/...`, so each opened checkout resolves its own.
- `.gitignore`, `.dockerignore`, `search.exclude`, and the lint prunes cover
  `.venv`.
- `agentdev-runtime project sync` removes `.venv` only when it is a symlink
  **and** its target is under `/uv/venvs/`, the shape earlier revisions created
  when the environment was shared. Left in place, such a link would keep the
  checkout on the shared environment. A real directory, or a link a developer
  pointed elsewhere, is reported and left in place.
- The deploy runtime serves exactly one workspace and keeps its fixed
  `UV_PROJECT_ENVIRONMENT`; nothing else can share it.

## Rejected alternatives

**One environment at a fixed path on the `/uv` volume.** Keeps cache and
environment on one filesystem, so packages hardlink instead of copying.
Rejected: every checkout in the container shares it, so concurrent worktrees
swap each other's editable installs mid-run.

**A per-checkout path on the `/uv` volume** (for example keyed on the workspace
folder name). Keeps hardlinking and isolates checkouts. Rejected: the path must
be derived per checkout in the container environment and in four VS Code
settings, and `.claude/worktrees/` checkouts are created after the container
starts, so nothing set at container creation can name them.

**Keep a `.venv` symlink to an out-of-tree environment.** Rejected earlier, and
still: a second name for one environment that goes stale when its target moves.
