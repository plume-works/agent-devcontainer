---
type: plan
created: 2026-11-01
release:
- bugs/shared-uv-environment-across-worktrees
- features/uv-run-only-environment
description: Give every checkout in a devcontainer its own uv environment — a .venv link into a per-checkout directory on the /uv volume, hardlinked to the cache there — created by one agentdev-runtime subcommand that git's post-checkout hook, the agentdev plugin's SessionStart and SubagentStart hooks, and the attach phase call.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T03:30:00Z
sources:
- resource: .devcontainer/devcontainer.json
- resource: py_packages/agentdev_runtime/agentdev_runtime/project.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: .pre-commit-config.yaml
- resource: https://code.claude.com/docs/en/hooks
rank: 450
---

# Give each checkout its own uv environment

## Context

[Bug: worktrees in one devcontainer share the uv
environment](../bugs/shared-uv-environment-across-worktrees.md): every checkout
in a devcontainer — the main one and each `.claude/worktrees/*` — uses
`/uv/venvs/ws-project`, and each `uv run` repoints its editable installs and
exact-synced dependencies at the invoking checkout, so concurrent sessions run
each other's code. Agent sessions create worktrees on their own: a session
started from claude.ai, a subagent dispatched with `isolation: worktree` by
implement-all, or a merge of an unrelated pull request. This applies to Mac
checkouts as much as to Coder workspaces.

This plan changes [uv-run-only
environment](../features/uv-run-only-environment.md): the environment stops
being one fixed path and becomes one per checkout. [uv environment
location](../architecture/uv-environment-location.md) records the current
design, whose premise — one `/uv` per devcontainer instance, so nothing to
disambiguate — does not hold for worktrees inside the container.

## Approach

Each checkout gets `.venv` as a symlink to
`/uv/venvs/<checkout directory name>`. The environment and the uv cache
(`/uv/cache`) share the `/uv` mount, so uv hardlinks packages instead of copying
them. Only the link sits in the checkout, so a macOS VirtioFS bind mount carries
no uv I/O. `UV_PROJECT_ENVIRONMENT` leaves the devcontainer descriptor, because
uv ignores `.venv` while it is set.

One idempotent subcommand, `agentdev-runtime project link-venv`, creates the
target directory first — uv fails on a `.venv` link whose target does not exist
— then the link. Four triggers call it, because no single event sees every
checkout:

| Trigger                                            | Checkouts it covers                                               |
| -------------------------------------------------- | ----------------------------------------------------------------- |
| git `post-checkout`, installed by pre-commit       | `git worktree add` by OpenCode, a person, or a script             |
| agentdev plugin `SessionStart` hook                | Claude sessions, including claude.ai and Remote Control worktrees |
| agentdev plugin `SubagentStart` hook, on its `cwd` | subagents dispatched with `isolation: worktree`                   |
| attach (`agentdev-runtime project sync`)           | the main checkout                                                 |

Claude Code creates its worktrees without a checkout step
(`git worktree add --no-checkout`, then `git reset`), so git's hooks never run
for them; the Claude hooks cover that path. `SubagentStart` receives the
subagent's own worktree as `cwd`, already populated.

Rejected, with the reasons recorded in the architecture document by Task 9: one
shared environment without editable installs (dependencies still diverge between
branches); a per-checkout `UV_PROJECT_ENVIRONMENT` set by a `uv` wrapper or by
`CLAUDE_ENV_FILE` (session-scoped and brittle); the uv cache inside the checkout
with an in-tree `.venv` (on macOS it puts uv's file-heavy state on VirtioFS and
clashes with a host `.venv`); `UV_LINK_MODE=symlink` (a cache clean breaks every
environment); a `PreToolUse` hook (runs on every tool call); a `WorktreeCreate`
hook (replaces Claude Code's own worktree creation); sweeping every worktree
from a hook rather than targeting the one at hand.

Assumptions: the environment root is a setting, `AGENTDEV_VENV_ROOT`, defaulting
to `/uv/venvs`, so the home-volume plan can move it; an environment is stale
when no checkout in `git worktree list` has its directory name; the retired
`ws-project` environment is removed as stale.

## Implementation Steps

### Task 1: Confirm the link survives a macOS VirtioFS bind mount

**Files:** none

- [ ] On a Mac running Docker Desktop with this devcontainer, a `.venv` link in
  the bind-mounted checkout that points to a directory under `/uv/venvs` is
  followed by `uv run python -c 'import sys; print(sys.prefix)'` inside the
  container, and a `.venv` file listing shows hardlinked packages (link count of
  2 or more).

### Task 2: Add the `project link-venv` subcommand

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/project.py`,
`py_packages/agentdev_runtime/agentdev_runtime/settings.py`,
`scripts/tests/test_agent_runtime_workspace.py`

- [ ] `agentdev-runtime project link-venv [PATH]` resolves the checkout root of
  `PATH` (default: the working directory), creates
  `$AGENTDEV_VENV_ROOT/<checkout directory name>`, and links `.venv` to it when
  `.venv` is absent. It repairs a link that points elsewhere under the root,
  leaves a real directory or a link outside the root in place with a warning,
  and exits 0 without changes in deploy mode, outside a git checkout, or when
  the root's parent does not exist.
- [ ] `AGENTDEV_VENV_ROOT` is a documented setting defaulting to `/uv/venvs`.
- [ ] Tests cover a fresh checkout, a second run (no change), a dangling link, a
  link elsewhere under the root, a real `.venv` directory, a foreign link, and
  deploy mode.

### Task 3: Link the main checkout on attach

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/project.py`,
`scripts/tests/test_agent_runtime_workspace.py`

- [ ] `project sync` links `.venv` through `link-venv` before `uv sync` instead
  of removing links under `/uv/venvs/`. A real `.venv` directory that holds a
  `pyvenv.cfg` is replaced by the link; any other real `.venv` is left with a
  warning.
- [ ] `test_standalone_skips_the_venv_migration` and the sync tests describe the
  new behavior.

### Task 4: Remove stale environments on attach

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/project.py`,
`scripts/tests/test_agent_runtime_workspace.py`

- [ ] `project sync` removes each directory under `$AGENTDEV_VENV_ROOT` whose
  name matches no checkout in `git worktree list`, and never one a listed
  checkout's `.venv` links to.
- [ ] Tests cover a removed worktree's environment, a live worktree's
  environment, and the retired `ws-project`.

### Task 5: Link new worktrees from git's post-checkout hook

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/project.py`,
`.pre-commit-config.yaml`, `scripts/tests/test_agent_runtime_workspace.py`

- [ ] `HOOK_TYPES` includes `post-checkout`, so `project hooks` installs it.
- [ ] A local `language: system` hook at stage `post-checkout` runs
  `agentdev-runtime project link-venv` with `always_run: true` and
  `pass_filenames: false`.
- [ ] A test runs `git worktree add` in a fixture repository with the installed
  hooks and finds the new worktree's `.venv` linked.

### Task 6: Link Claude session and subagent worktrees from plugin hooks

**Files:** Create: `.agents/plugins/agentdev/hooks/hooks.json`,
`.agents/plugins/agentdev/bin/link_venv_hook.py`,
`.agents/plugins/agentdev/tests/test_link_venv_hook.py`; Modify:
`.agents/plugins/agentdev/.claude-plugin/plugin.json`,
`.agents/plugins/agentdev/.codex-plugin/plugin.json`

- [ ] The plugin registers `SessionStart` and `SubagentStart` command hooks that
  run `link_venv_hook.py`.
- [ ] `link_venv_hook.py` reads the hook input's `cwd`, runs
  `agentdev-runtime project link-venv <cwd>` when `agentdev-runtime` is on
  `PATH`, prints nothing, and exits 0 whatever happens.
- [ ] Plugin tests cover a `cwd` that gets linked, a host without
  `agentdev-runtime`, and malformed input.
- [ ] Every plugin manifest the catalog still ships carries the same bumped
  version, and
  `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes.

### Task 7: Drop the shared environment from the descriptor

**Files:** Modify: `.devcontainer/devcontainer.json`

- [ ] `containerEnv` sets no `UV_PROJECT_ENVIRONMENT`.
- [ ] `python.defaultInterpreterPath`, `ansible.ansible.path`,
  `ansible.python.interpreterPath`, and `ansible.validation.lint.path` name
  `${workspaceFolder}/.venv/bin/...`.

### Task 8: Revise the home-volume plan's uv layout

**Files:** Modify:
`docs/knowledge/data/plans/20261030-devcontainer-home-volume.md`

- [ ] Through `/agentdev:iwe-plan` revise mode, the home-volume plan's uv tasks
  move `AGENTDEV_VENV_ROOT` and the uv cache onto the home volume together and
  set no fixed `UV_PROJECT_ENVIRONMENT` for the Dev Container.

### Task 9: Record the per-checkout environment design

**Files:** Modify:
`docs/knowledge/data/architecture/uv-environment-location.md`,
`docs/knowledge/data/features/uv-run-only-environment.md`

- [ ] The architecture document states the per-checkout link design, the four
  triggers and why each exists, and the rejected alternatives from
  `## Approach`.
- [ ] The feature document's Behaviour and Edge cases describe one environment
  per checkout.

### Task 10: Verify in a rebuilt Coder workspace

**Files:** none

- [ ] In a workspace rebuilt from this branch's image, a new Claude session's
  worktree, a subagent worktree from `isolation: worktree`, and a
  `git worktree add` worktree each get a `.venv` link to their own directory
  under `/uv/venvs`, with hardlinked packages after one `uv run`.
- [ ] Two worktrees with different `agentdev_runtime` code each import their own
  copy from
  `uv run python -c 'import agentdev_runtime; print(agentdev_runtime.__file__)'`
  while the other runs `uv sync`.

## Spec changes

[agentdev runtime images](../spec/agentdev-runtime-images.md):

``` markdown
## ADDED Requirements

### Requirement: each checkout has its own project environment

The Dev Container SHALL give every checkout of the workspace repository,
including each Git worktree, its own uv project environment: `.venv` in the
checkout SHALL be a link to a directory named after the checkout under
`AGENTDEV_VENV_ROOT` (default `/uv/venvs`), on the same volume as the uv cache.
The link SHALL exist before a worktree's first command when the worktree is made
by `git worktree add`, by a Claude Code session, or by a Claude Code subagent
dispatched with worktree isolation, and the attach phase SHALL create it for the
workspace folder. Attach SHALL remove environments that no listed checkout uses.

#### Scenario: two worktrees run uv at once

- **WHEN** two worktrees with different versions of the project's packages run
  `uv run` concurrently
- **THEN** each imports its own checkout's packages, and neither sync changes
  the other's environment

#### Scenario: an agent creates a worktree

- **WHEN** a Claude Code session or a worktree-isolated subagent starts in a new
  worktree
- **THEN** `.venv` links to that worktree's own environment before its first
  tool call

#### Scenario: a worktree is removed

- **WHEN** a worktree is removed and the workspace is next attached
- **THEN** its environment directory is deleted, and no listed checkout's
  environment is touched
```

## Verification

- `uv run pytest -n 8 scripts/tests/test_agent_runtime_workspace.py`
- `uv run pytest .agents/plugins/agentdev/tests/test_link_venv_hook.py`
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
- `.agents/plugins/agentdev/bin/python_lint_check.py`
- Task 1 on a Mac and Task 10 on a rebuilt Coder workspace, each recorded under
  `## Verification results`.

## Out of scope

- The deploy runtime: it serves one workspace and keeps its fixed
  `UV_PROJECT_ENVIRONMENT`.
- Codex sessions: [Claude and OpenCode only
  harnesses](../features/claude-and-opencode-only-harnesses.md) removes Codex.
- A consumer's own `.pre-commit-config.yaml`: the `post-checkout` hook entry
  ships in this repository's config only; consumers adopt it through their own
  configuration.
- Host and CI checkouts, which keep uv's default in-tree `.venv`.

## Key references

Verified anchor points (line numbers as of 2026-11-01):

- `.devcontainer/devcontainer.json:49` — `UV_PROJECT_ENVIRONMENT`
- `.devcontainer/devcontainer.json:172` — `python.defaultInterpreterPath`
- `.devcontainer/devcontainer.json:187` — `ansible.ansible.path`, with the two
  other `ansible.*` paths below it
- `py_packages/agentdev_runtime/agentdev_runtime/project.py:21` — `HOOK_TYPES`
- `py_packages/agentdev_runtime/agentdev_runtime/project.py:23` —
  `MANAGED_VENV_PREFIX`
- `py_packages/agentdev_runtime/agentdev_runtime/project.py:31` — `sync`
- `py_packages/agentdev_runtime/agentdev_runtime/project.py:82` — `hooks`
- `py_packages/agentdev_runtime/agentdev_runtime/project.py:142` — `main`
- `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py:168` — `attached`
  calls `project.sync`
- `py_packages/agentdev_runtime/agentdev_runtime/settings.py:284` —
  `UV_PROJECT_ENVIRONMENT` setting
- `scripts/tests/test_agent_runtime_workspace.py:259` —
  `test_standalone_skips_the_venv_migration`
- `.pre-commit-config.yaml:52` — `repo: local`
