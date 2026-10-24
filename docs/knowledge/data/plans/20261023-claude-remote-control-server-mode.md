---
type: plan
created: 2026-10-23
release:
- features/claude-remote-control-server-mode
description: Let AGENTDEV_CLAUDE_RC_MODE=server make claude-remote-control-start.sh run `claude remote-control --spawn same-dir` in the claude-remote tmux session in place of the pinned interactive pane, keeping the pinned pane as the default.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-24T00:16:39Z
sources:
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: scripts/tests/test_claude_remote_control_start.py
- resource: https://code.claude.com/docs/en/remote-control
- resource: https://code.claude.com/docs/en/claude-projects
---

# Opt-in Claude Remote Control server mode

## Context

[Remote Control server mode](../features/claude-remote-control-server-mode.md)
proposes letting a workspace accept new conversations from claude.ai/code, the
Claude mobile app, or a claude.ai Project. Today the autostarted `claude-remote`
pane serves one pinned conversation ([Claude Remote Control
resume](../architecture/claude-remote-control-resume.md)), under the contract in
[Claude Remote Control](../spec/claude-remote-control.md). The maintainer chose
an opt-in trial run that keeps the pinned pane as the default, with
`--spawn same-dir` as the only spawn mode.

## Approach

`claude-remote-control-start.sh` reads `AGENTDEV_CLAUDE_RC_MODE`. With `server`,
the pane command becomes `claude remote-control --spawn same-dir`, plus `--name`
and `--remote-control-session-name-prefix` set to `CODER_WORKSPACE_NAME` when
that is set. The command still runs under `exec env -u CLAUDE_CODE_OAUTH_TOKEN`
on the `tmux -L claude-remote` server, so the auth gate, the session reuse, and
the environment inheritance stay as they are. Unset or `session` keeps
`claude-remote-control-session.sh`. Any other value is checked first, before the
auth gate and the reuse check: the script prints the value and the valid
options, `server` and `session`, to stderr, starts nothing, and exits non-zero,
so the `coder_script` reports the misconfiguration.

Server mode does not use the pin hook or the stored conversation ID: the server
refuses `--settings` (Claude Code 2.1.309), and it brings back its own sessions
on restart. `--spawn` is always passed, because without a saved choice the
server stops at an interactive spawn-mode prompt.

Rejected alternatives:

- **Replacing the pinned pane.** Server mode resumes sessions only for about
  four hours after it stops, so an overnight workspace stop would lose the
  conversation the pinned pane keeps indefinitely.
- **Running a server next to the pinned pane.** It doubles the Remote Control
  entries and the processes that refresh the login before the refresh question
  in the feature is answered.
- **`--spawn worktree`.** A spawned worktree session does not survive a server
  restart (Claude Code 2.1.309), so it would lose exactly what server mode
  brings back.
- **Falling back to session mode on an unrecognized value.** The maintainer
  chose a failed startup, so a mistyped mode is reported instead of silently
  running the other mode.

## Implementation Steps

### Task 1: The start script selects server mode

**Files:** Modify: `.devcontainer/scripts/claude-remote-control-start.sh`,
`scripts/tests/test_claude_remote_control_start.py`

- [x] Add failing tests, using the existing fake-tmux harness, that
  `AGENTDEV_CLAUDE_RC_MODE=server` starts the pane with
  `exec env -u CLAUDE_CODE_OAUTH_TOKEN claude remote-control --spawn same-dir`,
  with and without `CODER_WORKSPACE_NAME` (which adds `--name` and
  `--remote-control-session-name-prefix` with the workspace name)
  - **Evidence:** commit "Select Remote Control server mode in the start
    script": `test_server_mode_starts_remote_control_server`, both cases failed
    before the script change.
- [x] Add tests that unset and `session` start
  `claude-remote-control-session.sh`, the session-mode pane command
  - **Evidence:** commit "Select Remote Control server mode in the start
    script": `test_session_mode_starts_pinned_pane`, unset and `session` cases.
- [x] Add tests that an unrecognized value exits non-zero, prints the value and
  the valid options `server` and `session` to stderr, and makes no tmux call,
  with and without a live `claude-remote` session
  - **Evidence:** commit "Select Remote Control server mode in the start
    script": `test_unrecognized_mode_fails_without_tmux`, both cases failed
    before the script change.
- [x] Add a test that a live `claude-remote` session is reused in server mode
  - **Evidence:** commit "Select Remote Control server mode in the start
    script": `test_server_mode_reuses_existing_session`.
- [x] Implement the mode selection in `claude-remote-control-start.sh`; the new
  tests and the existing ones pass with
  `uv run pytest scripts/tests/test_claude_remote_control_start.py`, and
  `shellcheck` passes
  - **Evidence:** commit "Select Remote Control server mode in the start
    script": the test file 17 passed; `shellcheck` clean.

### Task 2: Record the server-mode decision

**Files:** Create:
`docs/knowledge/data/architecture/claude-remote-control-server-mode.md`; Modify:
`docs/knowledge/data/architecture.md`

- [x] Write the architecture document: the opt-in decision and who made it, the
  `same-dir` default, the Claude Code server-mode behavior it relies on (as of
  Claude Code 2.1.309: `--settings` is refused; without `--spawn` and a saved
  choice the server prompts for a spawn mode; the existing preapproved trust and
  Remote Control confirmation suffice; each session is a child `claude` process
  inheriting the server's environment and with access to the credential store;
  the pre-created session returns under the same ID after a restart; a spawned
  worktree session does not), the documented limits (about four hours of resume
  after a stop, exit after about ten minutes offline), and the rejected
  alternatives from `## Approach`
  - **Evidence:** commit "Record the Remote Control server-mode decision":
    `data/architecture/claude-remote-control-server-mode.md`.
- [x] Link it from `data/architecture.md`; `iwe normalize` and
  `iwe schema validate` pass
  - **Evidence:** commit "Record the Remote Control server-mode decision":
    linked after Claude Remote Control resume; `iwe normalize` clean and
    `iwe schema validate` exit 0.

### Task 3: Server mode runs in a Coder workspace

**Files:** none

- [ ] With `AGENTDEV_CLAUDE_RC_MODE=server` as a Coder env user secret, a
  workspace restart starts the server in `claude-remote` with no terminal
  interaction; a conversation spawned from claude.ai/code works in the workspace
  folder and `gh auth status` succeeds in it; after a second workspace restart
  within the hour, the pre-created conversation answers with its earlier turns

## Spec changes

[Claude Remote Control](../spec/claude-remote-control.md): the autostart
requirement makes pinned-conversation resume specific to session mode, and a new
requirement adds server mode.

``` markdown
## MODIFIED Requirements

### Requirement: Remote Control autostarts only on a live claude.ai login

`claude-remote-control-start.sh` SHALL start Remote Control in exactly one
detached tmux session named `claude-remote`, on the dedicated tmux server
`tmux -L claude-remote`, naming the Remote Control session after
`CODER_WORKSPACE_NAME` when it is set, only when `claude auth status --json`
reports `loggedIn: true` with `authMethod: "claude.ai"`. The Coder template's
`coder_script` on the dev container's sub-agent runs it on every agent start; no
devcontainer lifecycle hook runs it. Repeated or concurrent runs SHALL reuse a
live session rather than create another. It SHALL skip startup when `claude` or
`tmux` is unavailable. The Claude process SHALL NOT receive
`CLAUDE_CODE_OAUTH_TOKEN`.

In session mode, the session SHALL resume the conversation whose ID is stored in
`remote-control-session-id` under Claude's configuration directory. When no ID
is stored, or the resume exits non-zero, it SHALL start a new conversation under
a newly generated ID and store that ID in place of the old one. Whenever the
session's conversation changes while Claude runs, including through `/clear`,
the session SHALL store the new conversation's ID in place of the old one; no
other Claude process SHALL write the stored ID. A transient failure to reconnect
a resumed conversation leaves Claude running with Remote Control off; running
`/remote-control` in the session restores it.

#### Scenario: the Coder agent restarts

- **WHEN** the `coder_script` runs while `claude-remote` is already live
- **THEN** it leaves the existing session running and creates no additional
  Claude process.

#### Scenario: the saved login has expired

- **WHEN** the credential file exists but `claude auth status --json` reports
  `loggedIn: false`
- **THEN** no session is started and the script exits successfully.

#### Scenario: only a setup token is available

- **WHEN** `claude auth status --json` reports `loggedIn: true` with an
  `authMethod` other than `claude.ai`
- **THEN** no session is started.

#### Scenario: the operator logs in after the workspace started

- **WHEN** an operator completes `/login` and runs the script from a Coder
  terminal
- **THEN** `claude-remote` starts without a workspace restart.

#### Scenario: the session starts in a Coder workspace

- **WHEN** the script starts `claude-remote` with `CODER_WORKSPACE_NAME` set
- **THEN** claude.ai/code lists the Remote Control session under that workspace
  name.

#### Scenario: the workspace restarts or is rebuilt

- **WHEN** `claude-remote` starts in session mode with a stored conversation ID
  whose conversation still exists
- **THEN** it resumes that conversation, and claude.ai/code shows it under the
  same session URL with its earlier turns.

#### Scenario: the first start in a new volume

- **WHEN** `claude-remote` starts in session mode with no stored conversation ID
- **THEN** it starts a new conversation and stores its ID.

#### Scenario: the stored conversation cannot be resumed

- **WHEN** resuming the stored conversation exits non-zero
- **THEN** a new conversation starts under a new ID, and that ID replaces the
  stored one.

#### Scenario: the operator clears the conversation

- **WHEN** `/clear` runs in `claude-remote` in session mode and the workspace
  then restarts
- **THEN** the pane resumes the post-clear conversation under the same session
  URL.

## ADDED Requirements

### Requirement: server mode is opt-in

`AGENTDEV_CLAUDE_RC_MODE` SHALL select the mode: `server` selects server mode,
and an unset or `session` value selects session mode. Any other value SHALL make
the script print the value and the valid options to stderr, start no session,
and exit non-zero, before any other check. In server mode the
`claude-remote` session SHALL run `claude remote-control --spawn same-dir`,
passing `--name` and `--remote-control-session-name-prefix` set to
`CODER_WORKSPACE_NAME` when it is set, and SHALL neither read nor write the
stored conversation ID.

#### Scenario: server mode is selected

- **WHEN** the script starts `claude-remote` with
  `AGENTDEV_CLAUDE_RC_MODE=server`
- **THEN** the session runs `claude remote-control --spawn same-dir` and
  reaches a connected server with no terminal interaction.

#### Scenario: a conversation is spawned from a device

- **WHEN** a new conversation is started in the workspace's environment from
  claude.ai/code or the Claude mobile app
- **THEN** it runs in the workspace folder with the environment of the process
  that ran the script.

#### Scenario: the mode value is unrecognized

- **WHEN** the script runs with `AGENTDEV_CLAUDE_RC_MODE` set to a value other
  than `server` or `session`
- **THEN** it prints the value and the valid options `server` and `session`,
  starts no session, and exits non-zero.

#### Scenario: the mode changes while a session is live

- **WHEN** the script runs with a different mode while `claude-remote` is live
- **THEN** it leaves the existing session running, and the new mode applies on
  the next session start.
```

## Verification

- `uv run pytest scripts/tests/test_claude_remote_control_start.py` passes,
  including the new server-mode tests.
- `shellcheck .devcontainer/scripts/claude-remote-control-start.sh` passes.
- Task 3's manual run on a Coder workspace.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- `--spawn worktree` and any override that selects it.
- A supervisor that restarts the server after it exits on an extended outage.
- Settling whether concurrent spawned conversations race the OAuth refresh
  token; the feature keeps it as an open question.
- Changing the default away from session mode.

## Key references

Verified anchor points (line numbers as of 2026-10-23):

- `.devcontainer/scripts/claude-remote-control-start.sh:29` — `session`, the
  tmux session and socket name
- `.devcontainer/scripts/claude-remote-control-start.sh:32` — `pane_command`,
  the pinned-pane command and its workspace-name argument
- `.devcontainer/scripts/claude-remote-control-start.sh:37` — the live-session
  reuse check
- `.devcontainer/scripts/claude-remote-control-start.sh:43` — `tmux_start`, the
  `exec env -u CLAUDE_CODE_OAUTH_TOKEN` launch
- `.devcontainer/scripts/coder-agent-start.sh:21` — the Coder agent's exec of
  the start script
- `scripts/tests/test_claude_remote_control_start.py:33` — `run_with_fake_tmux`,
  the fake-tmux harness
- `scripts/tests/test_claude_remote_control_start.py:82` —
  `test_names_session_after_coder_workspace`
- `scripts/tests/test_claude_remote_control_start.py:116` —
  `test_reuses_existing_session`
