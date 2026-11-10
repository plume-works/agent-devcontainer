---
type: plan
created: 2026-11-10
release:
- features/claude-remote-control-server-mode
description: Make same-dir the spawn mode a Remote Control server uses when AGENTDEV_CLAUDE_RC_SPAWN is unset or empty; worktree stays a value set explicitly.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/remote_control.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/settings.py
- resource: docker/deploy/runtime.env.example
---

# Make same-dir the default Remote Control spawn mode

## Context

The maintainer decided the Dev Container gives git worktrees nothing of their
own: they share the checkout's uv environment and catalog. The per-checkout uv
environment and per-worktree catalog plans are cancelled, and
[bugs/shared-uv-environment-across-worktrees](../bugs/shared-uv-environment-across-worktrees.md)
is closed as won't fix. A [Remote Control
server](../features/claude-remote-control-server-mode.md) still spawns every
on-demand conversation in its own git worktree unless
`AGENTDEV_CLAUDE_RC_SPAWN=same-dir`, so by default it creates worktrees the Dev
Container gives nothing of their own. The maintainer decided the server spawns
in the workspace folder by default. The closed bug's `## Fix` calls several
worktrees of one checkout unsupported, but no architecture document records what
the maintainer decided, and worktrees themselves still work.

## Approach

`agentdev-runtime remote-control start` falls back to `same-dir` in place of
`worktree` when `AGENTDEV_CLAUDE_RC_SPAWN` is unset; the standalone watcher
already unsets a set-but-empty value before the start reads it, so empty
follows. `worktree` stays a valid value, and the set of valid values and the
error for any other value do not change. The variable's description in
`settings.py`, the README table rendered from it, the deploy env example, the
feature, and the server-mode architecture record name the new default.

Rejected: removing `worktree` as a value. The maintainer kept it as an explicit
opt-in.

`supervisor.py` only validates the value against `('worktree', 'same-dir')` and
states no default, so it does not change.

A server already running with the variable unset keeps `--spawn worktree` until
its next session start; after that, revived worktree sessions run in the
workspace folder, as [Claude Remote Control spawn mode
switch](../architecture/claude-remote-control-spawn-mode-switch.md) records.
Their worktrees and branches stay on disk.

The decision behind the change goes in a new architecture document,
`architecture/worktree-support`, the way `architecture/supported-harnesses`
records that Codex is unsupported, and the closed bug's `## Fix` links it.

## Implementation Steps

### Task 1: Fall back to same-dir when the spawn mode is unset

**Files:** Modify:
`py_packages/agentdev_runtime/agentdev_runtime/remote_control.py`,
`scripts/tests/test_claude_remote_control_start.py`,
`scripts/tests/test_runtime_remote_control.py`,
`scripts/tests/test_agent_runtime_acceptance.py`

- [x] `remote_control.py::start` reads `AGENTDEV_CLAUDE_RC_SPAWN` with the
  fallback `same-dir`.
  - **Evidence:**
    `uv run pytest scripts/tests/test_claude_remote_control_start.py::test_server_mode_starts_remote_control_server`
    (the `spawn-unset` cases fail against the `worktree` fallback).
- [x] `test_claude_remote_control_start.py::test_server_mode_starts_remote_control_server`
  expects `--spawn same-dir` for the `spawn-unset` case.
  - **Evidence:**
    `uv run pytest scripts/tests/test_claude_remote_control_start.py::test_server_mode_starts_remote_control_server`
- [x] `test_runtime_remote_control.py::test_a_later_login_starts_the_session_once`
  and
  `test_runtime_remote_control.py::test_an_empty_spawn_mode_does_not_reach_the_start_script`
  expect `claude remote-control --spawn same-dir`.
  - **Evidence:**
    `uv run pytest scripts/tests/test_runtime_remote_control.py::test_a_later_login_starts_the_session_once scripts/tests/test_runtime_remote_control.py::test_an_empty_spawn_mode_does_not_reach_the_start_script`
- [ ] `test_agent_runtime_acceptance.py::test_remote_control_waits_for_a_login_then_starts_and_comes_back`
  expects the fake `claude` arguments to start with
  `remote-control --spawn same-dir`.

### Task 2: Name the new default where the variable is described

**Files:** Modify: `py_packages/agentdev_runtime/agentdev_runtime/settings.py`,
`py_packages/agentdev_runtime/README.md`, `docker/deploy/runtime.env.example`,
`docs/knowledge/data/features/claude-remote-control-server-mode.md`,
`docs/knowledge/data/architecture/claude-remote-control-server-mode.md`

- [ ] The `AGENTDEV_CLAUDE_RC_SPAWN` description in `settings.py::VARIABLES`
  reads ``Server-mode spawn, `same-dir` (empty) or `worktree`.``, and the
  matching row of the README table is the one `settings.py::markdown_table`
  renders.
- [ ] The `AGENTDEV_CLAUDE_RC_SPAWN` comment in `runtime.env.example` names
  `same-dir` as the empty value and `worktree` as the opt-in that gives each
  spawned conversation its own git worktree.
- [ ] `features/claude-remote-control-server-mode#behaviour` replaces "A
  worktree per conversation by default" with the workspace folder as the default
  and `AGENTDEV_CLAUDE_RC_SPAWN=worktree` as the opt-in.
- [ ] `architecture/claude-remote-control-server-mode` records the maintainer's
  decision that `same-dir` is the default because the Dev Container gives
  worktrees nothing of their own (linking `architecture/worktree-support`), in
  its description and decision paragraph, and replaces the rejected alternative
  about the worktree default with the worktree default itself: it spawns
  worktrees that share the checkout's uv environment and catalog.

### Task 3: Record that worktrees get no isolation of their own

**Files:** Create: `docs/knowledge/data/architecture/worktree-support.md`;
Modify: `docs/knowledge/data/architecture.md`,
`docs/knowledge/data/bugs/shared-uv-environment-across-worktrees.md`

- [x] `architecture/worktree-support` records, modelled on
  `architecture/supported-harnesses`, the maintainer's decision: worktrees still
  work (`git-new-branch --worktree`, `AGENTDEV_CLAUDE_RC_SPAWN=worktree`), but
  the Dev Container gives them nothing of their own — they share the checkout's
  uv environment and catalog. It names what the decision leaves in place
  (`git-new-branch --worktree`, the `worktree` spawn opt-in,
  `architecture/worktree-hooks`), and its rejected alternatives are the
  cancelled per-checkout uv environment and per-worktree catalog plans, linked
  inline. It is linked from `data/architecture.md` at its sorted position.
  - **Evidence:**
    `docs/knowledge/data/architecture/worktree-support.md#decision`,
    `#what-the-decision-leaves-in-place`, `#rejected-alternatives`;
    `docs/knowledge/data/architecture.md` › "[Worktree
    support](architecture/worktree-support.md)"
- [x] The `## Fix` of `bugs/shared-uv-environment-across-worktrees` says the bug
  is won't fix because worktrees share the checkout's uv environment by
  decision, and links `architecture/worktree-support`; it no longer calls
  several worktrees unsupported.
  - **Evidence:**
    `docs/knowledge/data/bugs/shared-uv-environment-across-worktrees.md#fix` ›
    "Won't fix: by the maintainer's decision"

## Spec changes

[Claude Remote Control](../spec/claude-remote-control.md) — the default spawn
mode changes, which changes a compatibility default and the requirement's
scenario set.

``` markdown
## MODIFIED Requirements

### Requirement: server mode is opt-in

`AGENTDEV_CLAUDE_RC_MODE` SHALL select the mode: `server` selects server mode,
and an unset or `session` value selects session mode. Any other value SHALL make
the command print the value and the valid options to stderr, start no session,
and exit non-zero, before any other check. In server mode,
`AGENTDEV_CLAUDE_RC_SPAWN` SHALL select the spawn mode: an unset or `same-dir`
value selects `same-dir`, and `worktree` selects `worktree`. Any other value
SHALL make the command print the value and the valid options to stderr, start no
session, and exit non-zero, before any check other than the mode's. In session
mode the command SHALL NOT read `AGENTDEV_CLAUDE_RC_SPAWN`. In server mode the
`claude-remote` session SHALL run `claude remote-control --spawn <spawn mode>`,
passing `--name` and `--remote-control-session-name-prefix` set to
`CODER_WORKSPACE_NAME` when it is set, and SHALL neither read nor write the
stored conversation ID. `.claude/worktrees/` SHALL be ignored by git.

#### Scenario: server mode is selected

- **WHEN** the command starts `claude-remote` with
  `AGENTDEV_CLAUDE_RC_MODE=server` and `AGENTDEV_CLAUDE_RC_SPAWN` unset
- **THEN** the session runs `claude remote-control --spawn same-dir` and reaches
  a connected server with no terminal interaction.

#### Scenario: worktree spawn mode is selected

- **WHEN** the command starts `claude-remote` with
  `AGENTDEV_CLAUDE_RC_MODE=server` and `AGENTDEV_CLAUDE_RC_SPAWN=worktree`
- **THEN** the session runs `claude remote-control --spawn worktree`.

#### Scenario: a conversation is spawned in worktree mode

- **WHEN** a new conversation is started in the workspace's environment from
  claude.ai/code or the Claude mobile app while the server runs in worktree mode
- **THEN** it runs in its own git worktree under the workspace folder's
  `.claude/worktrees/` with the environment of the process that ran the command,
  and `git status` in the workspace folder lists none of its files.

#### Scenario: the server pre-creates its session in worktree mode

- **WHEN** `claude remote-control --spawn worktree` starts and creates its first
  session
- **THEN** that session runs in the workspace folder, not in a worktree; only
  conversations spawned after it get worktrees under `.claude/worktrees/`.

#### Scenario: a conversation is spawned in same-dir mode

- **WHEN** a new conversation is started in the workspace's environment from
  claude.ai/code or the Claude mobile app while the server runs in same-dir mode
- **THEN** it runs in the workspace folder with the environment of the process
  that ran the command.

#### Scenario: the mode value is unrecognized

- **WHEN** the command runs with `AGENTDEV_CLAUDE_RC_MODE` set to a value other
  than `server` or `session`
- **THEN** it prints the value and the valid options `server` and `session`,
  starts no session, and exits non-zero.

#### Scenario: the spawn value is unrecognized in server mode

- **WHEN** the command runs with `AGENTDEV_CLAUDE_RC_MODE=server` and
  `AGENTDEV_CLAUDE_RC_SPAWN` set to a value other than `worktree` or `same-dir`
- **THEN** it prints the value and the valid options `worktree` and `same-dir`,
  starts no session, and exits non-zero.

#### Scenario: the spawn value is set in session mode

- **WHEN** the command runs in session mode with `AGENTDEV_CLAUDE_RC_SPAWN` set
  to any value
- **THEN** it starts the pinned pane exactly as with the variable unset.

#### Scenario: the mode or spawn mode changes while a session is live

- **WHEN** the command runs with a different mode or spawn mode while
  `claude-remote` is live
- **THEN** it leaves the existing session running, and the new setting applies
  on the next session start.
```

The scenario "same-dir spawn mode is selected" becomes "worktree spawn mode is
selected": with `same-dir` the default, "server mode is selected" covers it, and
the explicit value worth a scenario is `worktree`.

## Verification

- `uv run pytest scripts/tests/test_claude_remote_control_start.py scripts/tests/test_runtime_remote_control.py py_packages/agentdev_runtime/tests/test_settings.py`
- `uv run python -c "from agentdev_runtime.settings import markdown_table; print(markdown_table())" | grep AGENTDEV_CLAUDE_RC_SPAWN`
  prints the row `py_packages/agentdev_runtime/README.md` carries.
- `grep -n "worktree" py_packages/agentdev_runtime/agentdev_runtime/remote_control.py docker/deploy/runtime.env.example docs/knowledge/data/features/claude-remote-control-server-mode.md`
  shows `worktree` only as the opt-in value, never as the default.
- `test_agent_runtime_acceptance.py::test_remote_control_waits_for_a_login_then_starts_and_comes_back`
  runs in the CI job `Dev Container runtime acceptance`, which needs Docker.
- `iwe schema validate` passes, and
  `iwe find --references data/architecture/worktree-support -f keys` lists
  `data/architecture` and `data/bugs/shared-uv-environment-across-worktrees`.

## Out of scope

- Removing the `worktree` spawn mode, `.claude/worktrees/` in `.gitignore`, or
  the worktree architecture records.
- Removing worktrees or `worktree-bridge-<session ID>` branches an earlier
  server created.
- `git-new-branch --worktree` and its open bugs, and
  `backlog/pr-merge-post-merge-cleanup`, which still hold under the decision.

## Key references

- `py_packages/agentdev_runtime/agentdev_runtime/remote_control.py::start` —
  reads `AGENTDEV_CLAUDE_RC_SPAWN` and validates it in server mode.
- `py_packages/agentdev_runtime/agentdev_runtime/remote_control.py::run` — the
  watcher unsets a set-but-empty spawn mode before the start.
- `py_packages/agentdev_runtime/agentdev_runtime/remote_control.py::pane_command`
  — builds `claude remote-control --spawn <spawn mode>`.
- `py_packages/agentdev_runtime/agentdev_runtime/supervisor.py::Settings.from_env`
  › "parse.choice('AGENTDEV_CLAUDE_RC_SPAWN', ('worktree', 'same-dir'))" —
  validation only, unchanged.
- `py_packages/agentdev_runtime/agentdev_runtime/settings.py::markdown_table` —
  renders the README settings table.
- `docker/deploy/runtime.env.example` › "AGENTDEV_CLAUDE_RC_SPAWN=" — the deploy
  env comment.
- `scripts/tests/test_claude_remote_control_start.py::test_server_mode_starts_remote_control_server`
- `scripts/tests/test_runtime_remote_control.py::test_an_empty_spawn_mode_does_not_reach_the_start_script`
- `docs/knowledge/data/spec/claude-remote-control.md#requirement-server-mode-is-opt-in`
- `docs/knowledge/data/architecture/claude-remote-control-spawn-mode-switch.md`
  — what a server does with earlier worktree sessions after the switch.
