---
type: plan
created: 2026-11-01
release:
- bugs/shared-uv-environment-across-worktrees
- features/uv-run-only-environment
description: Give every checkout in a devcontainer its own uv environment — a .venv link into a per-checkout directory on the /uv volume, hardlinked to the cache there — created by one agentdev-runtime subcommand that git's post-checkout hook, the Claude WorktreeCreate hook agentdev-runtime provides, and the attach phase call, and removed by the matching WorktreeRemove hook or the next attach.
sources:
- resource: .devcontainer/devcontainer.json
- resource: py_packages/agentdev_runtime/agentdev_runtime/project.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/claude_state.py
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
started from claude.ai, a subagent dispatched with `isolation: worktree`, or a
merge of an unrelated pull request. This applies to Mac checkouts as much as to
Coder workspaces.

This plan changes [uv-run-only
environment](../features/uv-run-only-environment.md): the environment stops
being one fixed path and becomes one per checkout. [uv environment
location](../architecture/uv-environment-location.md) records the current
design, whose premise — one `/uv` per devcontainer instance, so nothing to
disambiguate — does not hold for worktrees inside the container.

How a `WorktreeCreate` or `WorktreeRemove` hook is written — triggers, stdin,
the returned path, the default layout — is recorded in [Worktree
hooks](../architecture/worktree-hooks.md).

## Approach

Each checkout gets `.venv` as a symlink to
`/uv/venvs/<checkout directory name>`. The environment and the uv cache
(`/uv/cache`) share the `/uv` mount, so uv hardlinks packages instead of copying
them. Only the link sits in the checkout, so a macOS VirtioFS bind mount carries
no uv I/O. `UV_PROJECT_ENVIRONMENT` leaves the devcontainer descriptor, because
uv ignores `.venv` while it is set.

One idempotent subcommand, `agentdev-runtime project link-venv`, creates the
target directory first — uv fails on a `.venv` link whose target does not exist
— then the link. Three triggers call it, because no single event sees every
checkout:

| Trigger                                                     | Checkouts it covers                                                                                        |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| git `post-checkout`, installed by pre-commit                | `git worktree add` by OpenCode, a person, or a script                                                      |
| Claude `WorktreeCreate`, `agentdev-runtime worktree create` | `claude -w`, Remote Control worktree spawns, `/batch`, and subagents dispatched with `isolation: worktree` |
| attach (`agentdev-runtime project sync`)                    | the main checkout                                                                                          |

Claude Code creates its own worktrees without a checkout step, so git's hooks
never run for them unless a `WorktreeCreate` hook creates the worktree instead.
`agentdev-runtime worktree create` does, with the default layout from [Worktree
hooks](../architecture/worktree-hooks.md#writing-the-hooks), then runs
`link-venv` in the new worktree before Claude Code starts the session there. Its
own `git worktree add` also fires `post-checkout`; `link-venv` is idempotent, so
the second run changes nothing.

`agentdev-runtime worktree remove`, the `WorktreeRemove` hook, deletes the
worktree's environment and then the worktree. `WorktreeRemove` runs only for
worktrees a `WorktreeCreate` hook made, and git has no hook for
`git worktree remove`, so attach still removes every environment no listed
checkout uses.

The attach phase registers both hooks in the user's Claude settings
(`$CLAUDE_CONFIG_DIR/settings.json`) whenever the runtime is not in deploy mode,
for any workspace repository. This plan owns the hook's base; [Give each Claude
worktree its own agentdev catalog](20261103-per-worktree-catalog.md) adds its
catalog step inside the same two subcommands, and Task 12 revises that plan to
say so.

Rejected, with the reasons recorded in the architecture document by Task 13: one
shared environment without editable installs (dependencies still diverge between
branches); a per-checkout `UV_PROJECT_ENVIRONMENT` set by a `uv` wrapper or by
`CLAUDE_ENV_FILE` (session-scoped and brittle); the uv cache inside the checkout
with an in-tree `.venv` (on macOS it puts uv's file-heavy state on VirtioFS and
clashes with a host `.venv`); `UV_LINK_MODE=symlink` (a cache clean breaks every
environment); a `PreToolUse` hook (runs on every tool call); `SessionStart` and
`SubagentStart` hooks in the agentdev plugin (`SessionStart` runs on every
session start rather than once per worktree, `SubagentStart` fires on a dispatch
rather than on a worktree's creation, and a worktree session that disables the
shared plugin gets neither); sweeping every worktree from a hook rather than
targeting the one at hand.

Assumptions: the environment root is a setting, `AGENTDEV_VENV_ROOT`, defaulting
to `/uv/venvs`, so the home-volume plan can move it; an environment is stale
when no checkout in `git worktree list` has its directory name; the retired
`ws-project` environment is removed as stale; `worktree create` branches from
`HEAD` and reduces the worktree name to `[A-Za-z0-9._-]`; `worktree remove`
keeps the `worktree-<name>` branch; hook registration is idempotent and only
adds.

## Implementation Steps

### Task 1: Confirm the link survives a macOS VirtioFS bind mount

**Files:** none

- [ ] On a Mac running Docker Desktop with this devcontainer, a `.venv` link in
  the bind-mounted checkout that points to a directory under `/uv/venvs` is
  followed by `uv run python -c 'import sys; print(sys.prefix)'` inside the
  container, and a `.venv` file listing shows hardlinked packages (link count of
  2 or more).

### Task 2: Confirm the worktree hooks' triggers and removal input

**Files:** Modify: `docs/knowledge/data/architecture/worktree-hooks.md`

**Closed by:** the user, on agent-dev3, with recording `WorktreeCreate` and
`WorktreeRemove` command hooks in user settings that save their stdin to a file.

- [ ] A subagent dispatched with `isolation: worktree` runs the recording
  `WorktreeCreate` hook, and `data/architecture/worktree-hooks` lists it among
  the triggers.
- [ ] Remote Control's automatic cleanup of a spawned session's worktree runs
  the recording `WorktreeRemove` hook, and the stdin field naming the worktree
  path is recorded in `data/architecture/worktree-hooks`, replacing "not yet
  confirmed".

### Task 3: Add the `project link-venv` subcommand

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/project.py`,
`py_packages/agentdev_runtime/agentdev_runtime/settings.py`,
`py_packages/agentdev_runtime/README.md`; Create:
`py_packages/agentdev_runtime/tests/test_project_link_venv.py`

- [x] `agentdev-runtime project link-venv [PATH]` resolves the checkout root of
  `PATH` (default: the working directory), creates
  `$AGENTDEV_VENV_ROOT/<checkout directory name>`, and links `.venv` to it when
  `.venv` is absent. It repairs a link that points elsewhere under the root,
  leaves a real directory or a link outside the root in place with a warning,
  and exits 0 without changes in deploy mode, outside a git checkout, or when
  the root's parent does not exist.
  - **Evidence:** commit a65d1dea adds `project.py::link_venv` and its
    `link-venv` command;
    `uv run pytest py_packages/agentdev_runtime/tests/test_project_link_venv.py`
    passed 10 tests.
- [x] `AGENTDEV_VENV_ROOT` is a documented setting defaulting to `/uv/venvs`.
  - **Evidence:** commit a65d1dea adds the setting to `settings.py::VARIABLES`
    and the README settings table;
    `uv run pytest py_packages/agentdev_runtime/tests` passed 109 tests,
    `test_settings.py::test_the_readme_lists_every_variable` among them.
- [x] Tests cover a fresh checkout, a second run (no change), a dangling link, a
  link elsewhere under the root, a real `.venv` directory, a foreign link, and
  deploy mode.
  - **Evidence:** commit a65d1dea adds
    `py_packages/agentdev_runtime/tests/test_project_link_venv.py`, which covers
    each listed case plus a path outside a checkout, a missing root parent, and
    the command line; all 10 passed.

### Task 4: Link the main checkout on attach

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/project.py`,
`scripts/tests/test_agent_runtime_workspace.py`; Create:
`py_packages/agentdev_runtime/tests/test_project_sync.py`

- [x] `project sync` links `.venv` through `link-venv` before `uv sync` instead
  of removing links under `/uv/venvs/`. A real `.venv` directory that holds a
  `pyvenv.cfg` is replaced by the link; any other real `.venv` is left with a
  warning.
  - **Evidence:** commit f623ae99 changes `project.py::sync`;
    `uv run pytest py_packages/agentdev_runtime/tests/test_project_sync.py`
    passed 3 tests: sync runs in the linked environment, a real uv environment
    is replaced, another real `.venv` is left with a warning.
- [x] `test_standalone_skips_the_venv_migration` and the sync tests describe the
  new behavior.
  - **Evidence:** commit f623ae99 renames it
    `test_standalone_leaves_the_venv_link_alone` and adds
    `py_packages/agentdev_runtime/tests/test_project_sync.py`;
    `uv run pytest -n 8 scripts/tests/test_agent_runtime_workspace.py` passed 24
    tests.

### Task 5: Remove stale environments on attach

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/project.py`,
`py_packages/agentdev_runtime/tests/test_project_sync.py`

- [x] `project sync` removes each directory under `$AGENTDEV_VENV_ROOT` whose
  name matches no checkout in `git worktree list`, and never one a listed
  checkout's `.venv` links to.
  - **Evidence:** commit 11c4f693 adds `project.py::prune_venvs`, called from
    `project.py::sync`;
    `uv run pytest py_packages/agentdev_runtime/tests/test_project_sync.py`
    passed 7 tests.
- [x] Tests cover a removed worktree's environment, a live worktree's
  environment, and the retired `ws-project`.
  - **Evidence:** commit 11c4f693 adds
    `test_a_removed_worktrees_environment_is_deleted`,
    `test_a_live_worktrees_environment_is_kept`,
    `test_an_environment_a_checkout_links_to_is_kept`, and
    `test_the_retired_shared_environment_is_deleted` to
    `py_packages/agentdev_runtime/tests/test_project_sync.py`; all passed.

### Task 6: Link new worktrees from git's post-checkout hook

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/project.py`,
`.pre-commit-config.yaml`, `scripts/tests/test_agent_runtime_workspace.py`

- [x] `HOOK_TYPES` includes `post-checkout`, so `project hooks` installs it.
  - **Evidence:** commit ac4597a8 adds it to `project.py::HOOK_TYPES`;
    `uv run pytest -n 8 scripts/tests/test_agent_runtime_workspace.py` passed 25
    tests, `test_project_setup_runs_only_for_present_configuration` asserting
    `--hook-type=post-checkout`.
- [x] A local `language: system` hook at stage `post-checkout` runs
  `agentdev-runtime project link-venv` with `always_run: true` and
  `pass_filenames: false`.
  - **Evidence:** commit ac4597a8 adds the `link-venv` hook to
    `.pre-commit-config.yaml`; its entry exits 0 when `agentdev-runtime` is not
    on `PATH`, and a top-level `default_stages` keeps every hook that names no
    stages off `post-checkout`.
- [x] A test runs `git worktree add` in a fixture repository with the installed
  hooks and finds the new worktree's `.venv` linked.
  - **Evidence:** commit ac4597a8 adds
    `scripts/tests/test_agent_runtime_workspace.py::test_post_checkout_links_a_new_worktrees_venv`,
    which installs this repository's hooks with real pre-commit and runs
    `git worktree add`; it passed in
    `uv run pytest -n 8 scripts/tests/test_agent_runtime_workspace.py`.

### Task 7: `agentdev-runtime worktree create`

**Files:** Create: `py_packages/agentdev_runtime/agentdev_runtime/worktree.py`,
`py_packages/agentdev_runtime/tests/test_worktree_create.py`; Modify:
`py_packages/agentdev_runtime/agentdev_runtime/cli.py`

- [x] `worktree create` reads the hook's stdin JSON, resolves the repository
  from `cwd` with `git rev-parse --show-toplevel`, reduces `name` to
  `[A-Za-z0-9._-]`, runs
  `git worktree add -b worktree-<name> <repository>/.claude/worktrees/<name> HEAD`
  with git's output on stderr, runs `link-venv` in the new worktree, and prints
  the worktree's absolute path as its only stdout line.
  - **Evidence:** commit 263b7ac7 adds `worktree.py::create` and the `worktree`
    entry in `cli.py::PASSTHROUGH`;
    `uv run pytest py_packages/agentdev_runtime/tests/test_worktree_create.py`
    passed 5 tests, `test_a_worktree_is_created_with_its_venv_linked` checking
    the printed path, branch, and link.
- [x] A failing step removes the worktree and its branch, and exits non-zero
  with the reason on stderr.
  - **Evidence:** commit 263b7ac7;
    `test_a_failing_link_removes_the_worktree_and_its_branch`,
    `test_a_failing_worktree_add_fails_the_hook`, and
    `test_unreadable_input_fails_the_hook` in
    `py_packages/agentdev_runtime/tests/test_worktree_create.py` passed.
- [x] Tests run the subcommand against a fixture repository with
  `AGENTDEV_VENV_ROOT` in the test's scratch directory, covering a created
  worktree with its `.venv` linked, a name that needs reducing, and a
  `git worktree add` that fails.
  - **Evidence:** commit 263b7ac7 adds
    `py_packages/agentdev_runtime/tests/test_worktree_create.py`, which runs
    `python -m agentdev_runtime worktree create` on a scratch repository and
    venv root; the created, reduced-name, and failed-add cases passed.

### Task 8: `agentdev-runtime worktree remove`

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/worktree.py`;
Create: `py_packages/agentdev_runtime/tests/test_worktree_remove.py`

- [x] `worktree remove` reads the worktree path from the stdin field
  `worktree_path`, which the hooks reference documents and Task 2 confirms,
  deletes the directory the worktree's `.venv` links to when it lies under
  `$AGENTDEV_VENV_ROOT`, then runs `git worktree remove --force <path>`; the
  `worktree-<name>` branch stays.
  - **Evidence:** commit f3f51f08 adds `worktree.py::remove`;
    `test_a_created_worktree_is_removed_with_its_environment` in
    `py_packages/agentdev_runtime/tests/test_worktree_remove.py` passed,
    checking the environment and worktree are gone and `worktree-task` remains.
- [x] A worktree that is already gone, or has no `.venv` link, is not an error.
  - **Evidence:** commit f3f51f08; `test_a_gone_worktree_is_not_an_error` and
    `test_a_worktree_without_a_venv_link_is_removed` in
    `py_packages/agentdev_runtime/tests/test_worktree_remove.py` passed.
- [x] Tests run the subcommand against a worktree Task 7's subcommand made, and
  against a gone worktree.
  - **Evidence:** commit f3f51f08 adds
    `py_packages/agentdev_runtime/tests/test_worktree_remove.py`, which runs
    `worktree create` then `worktree remove` through
    `python -m agentdev_runtime`, and a gone worktree;
    `uv run pytest py_packages/agentdev_runtime/tests` passed 124 tests.

### Task 9: Register the worktree hooks on attach

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/worktree.py`,
`py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py`; Create:
`py_packages/agentdev_runtime/tests/test_worktree_register.py`

- [x] A `register` function writes one `WorktreeCreate` command hook
  (`agentdev-runtime worktree create`) and one `WorktreeRemove` command hook
  (`agentdev-runtime worktree remove`) into `$CLAUDE_CONFIG_DIR/settings.json`
  through `claude_state.update_json`, keeping every other key and every other
  hook, and adding nothing on a second run.
  - **Evidence:** commit a515d65c adds `worktree.py::register`, which writes
    through `claude_state.update_json`;
    `test_registering_twice_adds_each_hook_once_and_keeps_the_rest` in
    `py_packages/agentdev_runtime/tests/test_worktree_register.py` passed.
- [x] `lifecycle.attached` calls it unless the runtime is in deploy mode,
  whether or not the checkout ships a catalog.
  - **Evidence:** commit a515d65c calls `worktree.register` from
    `lifecycle.py::attached` under `agent_state.config_lock` unless
    `project.deploy`; `test_attach_registers_the_hooks_outside_deploy_mode`
    passed for both modes, with a checkout that ships no catalog.
- [x] Tests run `register` twice on a settings file holding unrelated hooks and
  keys, and run the attach-phase step in and out of deploy mode.
  - **Evidence:** commit a515d65c adds
    `py_packages/agentdev_runtime/tests/test_worktree_register.py`;
    `uv run pytest py_packages/agentdev_runtime/tests` passed 127 tests.

### Task 10: Drop the shared environment from the descriptor

**Files:** Modify: `.devcontainer/devcontainer.json`

- [x] `containerEnv` sets no `UV_PROJECT_ENVIRONMENT`.
  - **Evidence:** commit 3f3fc5b7 removes it from
    `.devcontainer/devcontainer.json`;
    `git grep -n UV_PROJECT_ENVIRONMENT .devcontainer` finds nothing.
- [x] `python.defaultInterpreterPath`, `ansible.ansible.path`,
  `ansible.python.interpreterPath`, and `ansible.validation.lint.path` name
  `${workspaceFolder}/.venv/bin/...`.
  - **Evidence:** commit 3f3fc5b7 points all four at
    `${workspaceFolder}/.venv/bin/...`; `git grep -n ws-project .devcontainer`
    finds nothing.

### Task 11: Revise the home-volume plan's uv layout

**Files:** Modify:
`docs/knowledge/data/plans/20261030-devcontainer-home-volume.md`

- [x] Through `/agentdev:iwe-plan` revise mode, the home-volume plan's uv tasks
  move `AGENTDEV_VENV_ROOT` and the uv cache onto the home volume together and
  set no fixed `UV_PROJECT_ENVIRONMENT` for the Dev Container.
  - **Evidence:** commit 707afaf1 revises
    `20261030-devcontainer-home-volume.md#approach` and its Task 6 to set
    `AGENTDEV_VENV_ROOT` to `/home/agent/.local/share/uv/venvs` beside uv's
    cache with no `UV_PROJECT_ENVIRONMENT`, and adds this plan to its
    `## Depends on`; the Durable Knowledge Auditor reported nothing to change,
    and `iwe schema validate` passed.

### Task 12: Revise the per-worktree catalog plan onto this hook

**Files:** Modify: `docs/knowledge/data/plans/20261103-per-worktree-catalog.md`

- [ ] Through `/agentdev:iwe-plan` revise mode, the per-worktree catalog plan
  adds its catalog step to this plan's `agentdev-runtime worktree create` and
  `worktree remove` instead of creating them, drops its own hook registration
  and its `WorktreeRemove` input task, and depends on this plan.

### Task 13: Record the per-checkout environment design

**Files:** Modify:
`docs/knowledge/data/architecture/uv-environment-location.md`,
`docs/knowledge/data/features/uv-run-only-environment.md`

- [ ] The architecture document states the per-checkout link design, the three
  triggers and why each exists, removal by `WorktreeRemove` and by attach, and
  the rejected alternatives from `## Approach`, and links
  `data/architecture/worktree-hooks`.
- [ ] The feature document's Behaviour and Edge cases describe one environment
  per checkout.

### Task 14: Verify in a rebuilt Coder workspace

**Files:** none

**Closed by:** the user, in a Coder workspace rebuilt from this branch's image.

- [ ] A Remote Control worktree session, a subagent worktree from
  `isolation: worktree`, and a `git worktree add` worktree each get a `.venv`
  link to their own directory under `/uv/venvs`, with hardlinked packages after
  one `uv run`.
- [ ] Two worktrees with different `agentdev_runtime` code each import their own
  copy from
  `uv run python -c 'import agentdev_runtime; print(agentdev_runtime.__file__)'`
  while the other runs `uv sync`.
- [ ] Remote Control's cleanup of the spawned session's worktree removes its
  directory under `/uv/venvs`.

## Spec changes

[agentdev runtime images](../spec/agentdev-runtime-images.md):

``` markdown
## ADDED Requirements

### Requirement: each checkout has its own project environment

The Dev Container SHALL give every checkout of the workspace repository,
including each Git worktree, its own uv project environment: `.venv` in the
checkout SHALL be a link to a directory named after the checkout under
`AGENTDEV_VENV_ROOT` (default `/uv/venvs`), on the same volume as the uv cache.
The attach phase SHALL register `agentdev-runtime worktree create` and
`agentdev-runtime worktree remove` as the user's Claude `WorktreeCreate` and
`WorktreeRemove` hooks. The link SHALL exist before a worktree's first command
when the worktree is made by `git worktree add` or by that `WorktreeCreate`
hook, and the attach phase SHALL create it for the workspace folder. The
`WorktreeRemove` hook SHALL delete the environment of the worktree it removes;
attach SHALL remove every other environment no listed checkout uses.

#### Scenario: two worktrees run uv at once

- **WHEN** two worktrees with different versions of the project's packages run
  `uv run` concurrently
- **THEN** each imports its own checkout's packages, and neither sync changes
  the other's environment

#### Scenario: an agent creates a worktree

- **WHEN** a Claude Code session or a worktree-isolated subagent starts in a new
  worktree
- **THEN** the worktree is at `.claude/worktrees/<name>` on branch
  `worktree-<name>`, and its `.venv` links to its own environment before the
  session starts

#### Scenario: Claude Code removes a worktree

- **WHEN** Claude Code removes a worktree its `WorktreeCreate` hook made
- **THEN** that worktree's environment directory is deleted at once, and its
  `worktree-<name>` branch is kept

#### Scenario: a worktree is removed outside Claude Code

- **WHEN** a worktree is removed with `git worktree remove` and the workspace is
  next attached
- **THEN** its environment directory is deleted, and no listed checkout's
  environment is touched
```

## Verification

- `uv run pytest -n 8 scripts/tests/test_agent_runtime_workspace.py`
- `uv run pytest py_packages/agentdev_runtime/tests/test_worktree_create.py py_packages/agentdev_runtime/tests/test_worktree_remove.py py_packages/agentdev_runtime/tests/test_worktree_register.py`
- `.agents/plugins/agentdev/bin/python_lint_check.py`
- Task 1 on a Mac, Task 2 on agent-dev3, and Task 14 on a rebuilt Coder
  workspace, each recorded under `## Verification results`.

## Out of scope

- The deploy runtime: it serves one workspace, keeps its fixed
  `UV_PROJECT_ENVIRONMENT`, and registers no worktree hooks.
- Per-worktree agentdev catalogs, which [Give each Claude worktree its own
  agentdev catalog](20261103-per-worktree-catalog.md) adds to this plan's
  worktree hooks.
- A consumer's own `.pre-commit-config.yaml`: the `post-checkout` hook entry
  ships in this repository's config only; consumers adopt it through their own
  configuration.
- Host and CI checkouts, which keep uv's default in-tree `.venv`.

## Key references

- `.devcontainer/devcontainer.json › "UV_PYTHON_INSTALL_DIR"` — the uv variables
  in `containerEnv`
- `.devcontainer/devcontainer.json › "ruff.lint.enable"` —
  `python.defaultInterpreterPath`
- `.devcontainer/devcontainer.json › "cmake.exportCompileCommandsFile"` —
  `ansible.ansible.path`, with the two other `ansible.*` paths below it
- `py_packages/agentdev_runtime/agentdev_runtime/project.py::HOOK_TYPES` —
  `HOOK_TYPES`
- `py_packages/agentdev_runtime/agentdev_runtime/project.py::deploy` — deploy
  mode check
- `py_packages/agentdev_runtime/agentdev_runtime/project.py::sync` — `sync`
- `py_packages/agentdev_runtime/agentdev_runtime/project.py::hooks` — `hooks`
- `py_packages/agentdev_runtime/agentdev_runtime/project.py::main` — `main`
- `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py::attached` —
  `attached` calls `project.sync`
- `py_packages/agentdev_runtime/agentdev_runtime/claude_state.py::update_json` —
  `update_json`
- `py_packages/agentdev_runtime/agentdev_runtime/remote_control.py::config_dir`
  — `config_dir`
- `py_packages/agentdev_runtime/agentdev_runtime/cli.py::PASSTHROUGH` —
  `PASSTHROUGH`
- `py_packages/agentdev_runtime/agentdev_runtime/settings.py::VARIABLES` —
  `UV_PROJECT_ENVIRONMENT` setting
- `scripts/tests/test_agent_runtime_workspace.py::test_standalone_leaves_the_venv_link_alone`
  — the deploy-mode `.venv` test
- `.pre-commit-config.yaml › "repo: local"` — `repo: local`
- `docs/knowledge/data/architecture/worktree-hooks.md#writing-the-hooks` — the
  default worktree layout
