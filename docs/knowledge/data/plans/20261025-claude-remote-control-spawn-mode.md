---
type: plan
created: 2026-10-25
release:
- features/claude-remote-control-server-mode
description: Let AGENTDEV_CLAUDE_RC_SPAWN choose the spawn mode of Remote Control server mode, worktree by default and same-dir on request, and keep spawned worktrees out of the main checkout's git status.
generated:
  by: claude-code/opus-5
  at: 2026-10-25T18:00:00Z
sources:
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: scripts/tests/test_claude_remote_control_start.py
- resource: .claude/.gitignore
- resource: https://code.claude.com/docs/en/remote-control
- resource: https://code.claude.com/docs/en/worktrees
---

# Configurable Remote Control spawn mode, worktree by default

## Context

[Remote Control server mode](../features/claude-remote-control-server-mode.md)
runs `claude remote-control --spawn same-dir`, so every conversation spawned
from claude.ai/code, the Claude app, or a claude.ai Project edits the same
workspace folder, and concurrent conversations collide on the same files. The
maintainer decided that server mode spawns each on-demand conversation in its
own git worktree by default, with `same-dir` still selectable. The pinned
session pane stays the default `AGENTDEV_CLAUDE_RC_MODE`; only the spawn mode of
server mode changes.

This replaces the `--spawn worktree` rejection in [Claude Remote Control server
mode](../architecture/claude-remote-control-server-mode.md). The maintainer's
position is that revival after a restart does not depend on the spawn mode: the
[restart resume
finding](../architecture/claude-remote-control-server-restart-resume.md)
measured that a `same-dir` session spawned on demand also stays disconnected
until the claude.ai service dispatches it, which can take minutes. Revival after
more than about four hours of server downtime is a separate open question in
that finding, independent of the spawn mode. Per the maintainer, sessions of a
running server stay live overnight; the four-hour window bounds downtime only.

The contract is [Claude Remote Control](../spec/claude-remote-control.md).

## Approach

`claude-remote-control-start.sh` reads a second variable,
`AGENTDEV_CLAUDE_RC_SPAWN`, only when `AGENTDEV_CLAUDE_RC_MODE` selects server
mode. Unset or `worktree` passes `--spawn worktree`; `same-dir` passes
`--spawn same-dir`. Any other value fails startup the way an unrecognized mode
does — value and valid options on stderr, no tmux call, non-zero exit — checked
right after the mode and before the tool and login checks. Session mode never
reads the variable, so a stale or mistyped value there has no effect; the
maintainer chose that over failing in a mode that does not use it.

`.claude/worktrees/`, where Claude Code creates spawned worktrees, is added to
`.claude/.gitignore`, so worktrees do not show up as untracked files in the main
checkout. The session the server pre-creates stays in the workspace folder in
both spawn modes; Claude Code documents this for `--create-session-in-dir`,
which is on by default.

Rejected alternatives:

- **Folding the spawn mode into `AGENTDEV_CLAUDE_RC_MODE`** (for example
  `server-same-dir`). It merges two independent choices into one value list that
  grows with every spawn mode.
- **A pass-through argument variable.** It would accept `--continue` or
  `--settings`, which server mode refuses and which end the pane.
- **Offering `--spawn session`.** Its name collides with
  `AGENTDEV_CLAUDE_RC_MODE=session`, and it serves one session and exits when
  that ends, which ends the pane.
- **Making the worktree default depend on a measured worktree revival.** The
  maintainer made worktree the default regardless; revival of a worktree session
  is an assumption, not a measured behaviour.

Assumptions:

- An empty `AGENTDEV_CLAUDE_RC_SPAWN` in server mode is unrecognized, matching
  how an empty `AGENTDEV_CLAUDE_RC_MODE` is treated.
- A workspace folder that is not a git repository gets no fallback to
  `same-dir`; worktree mode needs a git repository, and every workspace this
  template starts is one.

## Implementation Steps

### Task 1: The start script selects the spawn mode

**Files:** Modify: `.devcontainer/scripts/claude-remote-control-start.sh`,
`scripts/tests/test_claude_remote_control_start.py`

- [x] Extend `run_with_fake_tmux` with a `spawn` argument that sets
  `AGENTDEV_CLAUDE_RC_SPAWN`, and pop the variable from the inherited
  environment by default, as the harness does for `AGENTDEV_CLAUDE_RC_MODE`
  - **Evidence:** commit "Select the Remote Control spawn mode in the start
    script": `run_with_fake_tmux(spawn=...)`.
- [x] Change `test_server_mode_starts_remote_control_server` to expect
  `claude remote-control --spawn worktree` with `spawn` unset and with
  `worktree`, and `--spawn same-dir` with `same-dir`, each with and without
  `CODER_WORKSPACE_NAME`; the unset and `worktree` cases fail before the script
  change
  - **Evidence:** commit "Select the Remote Control spawn mode in the start
    script": six parametrized cases; the four unset and `worktree` cases failed
    before the script change.
- [x] Add a test that in server mode an unrecognized spawn value (`worktre`,
  empty) exits non-zero, prints the value and the valid options `worktree` and
  `same-dir` to stderr, and makes no tmux call, with and without a live
  `claude-remote` session
  - **Evidence:** commit "Select the Remote Control spawn mode in the start
    script": `test_unrecognized_spawn_fails_in_server_mode_without_tmux`, all
    four cases failed before the script change.
- [x] Add a test that in session mode (mode unset and `session`) an unrecognized
  spawn value still starts `claude-remote-control-session.sh`
  - **Evidence:** commit "Select the Remote Control spawn mode in the start
    script": `test_session_mode_ignores_unrecognized_spawn`, unset and `session`
    cases.
- [x] Implement the spawn-mode selection in `claude-remote-control-start.sh`;
  `uv run pytest scripts/tests/test_claude_remote_control_start.py` passes and
  `shellcheck .devcontainer/scripts/claude-remote-control-start.sh` is clean
  - **Evidence:** commit "Select the Remote Control spawn mode in the start
    script": the test file 29 passed; `shellcheck` clean.

### Task 2: Keep spawned worktrees out of the main checkout's status

**Files:** Modify: `.claude/.gitignore`

- [ ] Add `worktrees/` to `.claude/.gitignore`;
  `git check-ignore -q .claude/worktrees/example/file` succeeds

### Task 3: Record the spawn-mode decision

**Files:** Modify:
`docs/knowledge/data/architecture/claude-remote-control-server-mode.md`

- [ ] Rewrite the decision: server mode spawns on-demand conversations with
  `--spawn worktree` by default and `--spawn same-dir` when
  `AGENTDEV_CLAUDE_RC_SPAWN=same-dir`, decided by the maintainer; the
  pre-created session stays in the workspace folder; the spawn value is read
  only in server mode and an unrecognized one fails startup
- [ ] Remove "A spawned worktree session does not survive a restart" from the
  measured Claude Code behavior list, and add that worktree mode needs a git
  repository and creates worktrees under `.claude/worktrees/`
- [ ] Add a separate "Assumed, not measured" list, outside the measured one: a
  spawned session returns after a restart the same way in either spawn mode
  (measured for `same-dir` in the restart resume finding), and a revived
  worktree session re-enters its worktree
- [ ] Replace the `--spawn worktree` rejected alternative with this plan's
  rejected alternatives from `## Approach`; keep the other three
- [ ] Add to Consequences that a spawn-mode change, like a mode change, applies
  on the next session start, and that `.claude/worktrees/` is gitignored;
  `iwe normalize` and `iwe schema validate` pass

### Task 4: Update the feature

**Files:** Modify:
`docs/knowledge/data/features/claude-remote-control-server-mode.md`

- [ ] In `## Behaviour`, replace the `--spawn same-dir` command and the "Same
  directory" paragraph with the spawn-mode setting: each on-demand conversation
  in its own worktree by default, the workspace folder with
  `AGENTDEV_CLAUDE_RC_SPAWN=same-dir`, the pre-created conversation in the
  workspace folder either way
- [ ] In `## Edge cases`, replace "Worktree spawn mode. Not offered" with an
  unrecognized spawn value failing startup in server mode and being ignored in
  session mode; add to `## Open questions` whether worktrees of spawned
  conversations accumulate, since spawned sessions run as `claude --print`
  (restart resume finding) and Claude Code documents no worktree cleanup for
  `-p` runs; `iwe normalize` and `iwe schema validate` pass

### Task 5: Confirm both spawn modes on a Coder workspace

**Files:** none

- [ ] With `AGENTDEV_CLAUDE_RC_MODE=server` and `AGENTDEV_CLAUDE_RC_SPAWN`
  unset, a conversation started from claude.ai/code runs in a worktree under
  `.claude/worktrees/` on its own branch, `gh auth status` succeeds in it, its
  project MCP servers are connected, and `git status` in the workspace folder
  lists no worktree files, while the pre-created session works in the workspace
  folder; a missing MCP server is captured as a bug with
  `/agentdev:iwe-capture bug`
- [ ] With `AGENTDEV_CLAUDE_RC_SPAWN=same-dir` and a fresh `claude-remote`
  session, a conversation started from claude.ai/code runs in the workspace
  folder

### Task 6: Observe a worktree session across a server restart

**Files:** none

- [ ] In worktree mode, restart the server with a spawned worktree conversation
  live, wait for the service to dispatch it, and record in
  `## Verification results` whether it returned with its earlier turns and in
  which directory; a return outside its worktree is captured as a bug with
  `/agentdev:iwe-capture bug`

## Spec changes

[Claude Remote Control](../spec/claude-remote-control.md) — the server-mode
requirement gains the spawn mode and its validation:

``` markdown
## MODIFIED Requirements

### Requirement: server mode is opt-in

`AGENTDEV_CLAUDE_RC_MODE` SHALL select the mode: `server` selects server mode,
and an unset or `session` value selects session mode. Any other value SHALL make
the script print the value and the valid options to stderr, start no session,
and exit non-zero, before any other check. In server mode,
`AGENTDEV_CLAUDE_RC_SPAWN` SHALL select the spawn mode: an unset or `worktree`
value selects `worktree`, and `same-dir` selects `same-dir`. Any other value
SHALL make the script print the value and the valid options to stderr, start no
session, and exit non-zero, before any check other than the mode's. In session
mode the script SHALL NOT read `AGENTDEV_CLAUDE_RC_SPAWN`. In server mode the
`claude-remote` session SHALL run `claude remote-control --spawn <spawn mode>`,
passing `--name` and `--remote-control-session-name-prefix` set to
`CODER_WORKSPACE_NAME` when it is set, and SHALL neither read nor write the
stored conversation ID. `.claude/worktrees/` SHALL be ignored by git.

#### Scenario: server mode is selected

- **WHEN** the script starts `claude-remote` with
  `AGENTDEV_CLAUDE_RC_MODE=server` and `AGENTDEV_CLAUDE_RC_SPAWN` unset
- **THEN** the session runs `claude remote-control --spawn worktree` and
  reaches a connected server with no terminal interaction.

#### Scenario: same-dir spawn mode is selected

- **WHEN** the script starts `claude-remote` with
  `AGENTDEV_CLAUDE_RC_MODE=server` and `AGENTDEV_CLAUDE_RC_SPAWN=same-dir`
- **THEN** the session runs `claude remote-control --spawn same-dir`.

#### Scenario: a conversation is spawned in worktree mode

- **WHEN** a new conversation is started in the workspace's environment from
  claude.ai/code or the Claude mobile app while the server runs in worktree mode
- **THEN** it runs in its own git worktree under the workspace folder's
  `.claude/worktrees/` with the environment of the process that ran the script,
  and `git status` in the workspace folder lists none of its files.

#### Scenario: a conversation is spawned in same-dir mode

- **WHEN** a new conversation is started in the workspace's environment from
  claude.ai/code or the Claude mobile app while the server runs in same-dir mode
- **THEN** it runs in the workspace folder with the environment of the process
  that ran the script.

#### Scenario: the mode value is unrecognized

- **WHEN** the script runs with `AGENTDEV_CLAUDE_RC_MODE` set to a value other
  than `server` or `session`
- **THEN** it prints the value and the valid options `server` and `session`,
  starts no session, and exits non-zero.

#### Scenario: the spawn value is unrecognized in server mode

- **WHEN** the script runs with `AGENTDEV_CLAUDE_RC_MODE=server` and
  `AGENTDEV_CLAUDE_RC_SPAWN` set to a value other than `worktree` or `same-dir`
- **THEN** it prints the value and the valid options `worktree` and
  `same-dir`, starts no session, and exits non-zero.

#### Scenario: the spawn value is set in session mode

- **WHEN** the script runs in session mode with `AGENTDEV_CLAUDE_RC_SPAWN` set
  to any value
- **THEN** it starts the pinned pane exactly as with the variable unset.

#### Scenario: the mode or spawn mode changes while a session is live

- **WHEN** the script runs with a different mode or spawn mode while
  `claude-remote` is live
- **THEN** it leaves the existing session running, and the new setting applies
  on the next session start.
```

Ship also updates the spec's `description`, which names server mode as a
spawn-on-demand server, if its wording no longer fits.

## Verification

- `uv run pytest scripts/tests/test_claude_remote_control_start.py` passes,
  including the spawn-mode tests.
- `shellcheck .devcontainer/scripts/claude-remote-control-start.sh` passes.
- `git check-ignore -q .claude/worktrees/example/file` succeeds.
- Tasks 5 and 6 on a Coder workspace.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Changing the default `AGENTDEV_CLAUDE_RC_MODE` away from session mode.
- `--spawn session`.
- Removing worktrees of finished spawned conversations; the feature keeps their
  accumulation as an open question.
- `worktree.baseRef`, `.worktreeinclude`, and per-worktree toolchain setup:
  spawned worktrees use Claude Code's defaults.
- Revival after more than about four hours of server downtime, an open question
  of the [restart resume
  finding](../architecture/claude-remote-control-server-restart-resume.md).
- Refreshing `data/codebase/devcontainer/scripts.md`, which `/agentdev:iwe-map`
  owns.

## Key references

Verified anchor points (line numbers as of 2026-10-25):

- `.devcontainer/scripts/claude-remote-control-start.sh:4` — `mode`, read from
  `AGENTDEV_CLAUDE_RC_MODE`, validated through line 9
- `.devcontainer/scripts/claude-remote-control-start.sh:11` — `spawn`, read from
  `AGENTDEV_CLAUDE_RC_SPAWN` in server mode only, validated through line 16
- `.devcontainer/scripts/claude-remote-control-start.sh:19` — the `claude` and
  `tmux` availability check the spawn validation precedes
- `.devcontainer/scripts/claude-remote-control-start.sh:50` — the server-mode
  branch; line 51 passes `--spawn $spawn`
- `scripts/tests/test_claude_remote_control_start.py:33` — `run_with_fake_tmux`;
  lines 65-72 pop and set `AGENTDEV_CLAUDE_RC_MODE` and
  `AGENTDEV_CLAUDE_RC_SPAWN`
- `scripts/tests/test_claude_remote_control_start.py:125` —
  `test_server_mode_starts_remote_control_server`, over the spawn modes
- `scripts/tests/test_claude_remote_control_start.py:157` —
  `test_unrecognized_spawn_fails_in_server_mode_without_tmux`
- `scripts/tests/test_claude_remote_control_start.py:167` —
  `test_session_mode_ignores_unrecognized_spawn`
- `.claude/.gitignore:1` — `*.local.json`, the file's only entry
