---
type: plan
created: 2026-10-13
description: Make the autostarted Claude Remote Control resume its own pinned conversation on every start, so a workspace restart or rebuild reattaches the same claude.ai/code session, falling back to a fresh pinned conversation when the resume exits non-zero.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-13T07:26:35Z
sources:
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: .devcontainer/devcontainer.json
- resource: scripts/tests/test_claude_remote_control_start.py
- resource: https://code.claude.com/docs/en/remote-control
stage: done
completed: 2026-10-13
---

# Resume the autostarted Remote Control conversation by a pinned ID

## Context

Each start of `claude-remote-control-start.sh` begins a new conversation, so
every workspace restart or rebuild lists another claude.ai/code session and the
previous chat goes offline for good. [Resume the Remote Control conversation
across restarts](../someday/claude-remote-control-resume.md) is the idea this
plan builds; [Claude Remote Control
resume](../architecture/claude-remote-control-resume.md) records the decision,
its rejected alternatives, and the Claude Code behavior it relies on.

## Approach

A new pane-side script, `claude-remote-control-session.sh`, becomes the process
the `claude-remote` tmux pane runs. It keeps the pinned conversation ID in
`${CLAUDE_CONFIG_DIR:-$HOME/.claude}/remote-control-session-id`, which is on the
per-instance `agentdev-claude` volume. With a stored ID it runs
`claude --remote-control [name] --resume <id>`. When there is no stored ID, or
the resume exits non-zero, it generates an ID from
`/proc/sys/kernel/random/uuid`, writes it to the ID file, and execs
`claude --remote-control [name] --session-id <id>`.
`claude-remote-control-start.sh` keeps its login gate, tmux server, session
reuse, and token removal, and starts the pane script in place of `claude`.

Assumptions: one stored ID per `agentdev-claude` volume is enough, because each
instance has one workspace folder. A missing or unreadable ID file means "no
stored ID".

## Implementation Steps

### Task 1: Pane script resumes or starts a pinned conversation

**Files:** Create: `.devcontainer/scripts/claude-remote-control-session.sh`,
`scripts/tests/test_claude_remote_control_session.py`

- [x] Tests first, against a fake `claude` that appends its arguments to a log
  and exits with a status the test sets; every test points `CLAUDE_CONFIG_DIR`
  at a temporary directory, never the real `~/.claude`:
  - no ID file: one call, `--remote-control <name> --session-id <uuid>`; the ID
    file holds that UUID;
  - ID file present, resume exits 0: one call,
    `--remote-control <name> --resume <stored>`; the ID file is unchanged;
  - ID file present, resume exits 1: a second call,
    `--remote-control <name> --session-id <new>` with `<new>` different from the
    stored ID; the ID file holds `<new>`;
  - no name argument: the calls carry `--remote-control` with no name.
  - **Evidence:** commit "Resume the Remote Control conversation by a pinned
    ID": `test_claude_remote_control_session.py`, one test per case; all four
    fail before the script exists.
- [x] Script: `#!/usr/bin/env bash`, `set -euo pipefail`; an optional first
  argument is the Remote Control name; behavior as in `## Approach`.
  - **Evidence:** commit "Resume the Remote Control conversation by a pinned
    ID": `claude-remote-control-session.sh`.
- [x] `shellcheck` clean;
  `uv run pytest scripts/tests/test_claude_remote_control_session.py` green.
  - **Evidence:** commit "Resume the Remote Control conversation by a pinned
    ID": `shellcheck` clean; the test file 4 passed.

### Task 2: Start script runs the pane script

**Files:** Modify: `.devcontainer/scripts/claude-remote-control-start.sh`,
`scripts/tests/test_claude_remote_control_start.py`

- [x] Tests: the fake-tmux cases expect the pane command to run
  `claude-remote-control-session.sh` from the script's own directory, with the
  `CODER_WORKSPACE_NAME` argument when set and `CLAUDE_CODE_OAUTH_TOKEN`
  removed; the real-tmux case sets `CLAUDE_CONFIG_DIR` to its test directory and
  still asserts the fake `claude` sees `--remote-control` first, no setup token,
  and the caller's environment marker.
  - **Evidence:** commit "Start the Remote Control pane through the session
    script": `PANE_SCRIPT` assertions in both fake-tmux cases fail against the
    previous script; the real-tmux case sets `CLAUDE_CONFIG_DIR`.
- [x] Script: replace `claude_command` with the pane script, located relative to
  `claude-remote-control-start.sh`.
  - **Evidence:** commit "Start the Remote Control pane through the session
    script": `pane_command` at `claude-remote-control-start.sh:31-35`.
- [x] `shellcheck` clean;
  `uv run pytest scripts/tests/test_claude_remote_control_start.py scripts/tests/test_claude_remote_control_session.py`
  green.
  - **Evidence:** commit "Start the Remote Control pane through the session
    script": `shellcheck` clean on both scripts; 14 passed, both real-tmux cases
    run.

### Task 3: Refresh the codebase map

**Files:** Modify: `docs/knowledge/data/codebase/devcontainer/scripts.md`, and
any other `data/codebase/` doc `stale-map-docs.py` reports

- [x] Run `/agentdev:iwe-map` in refresh mode over the docs that cover the two
  scripts, adding the pane script's row.
  - **Evidence:** commit "map: refresh devcontainer scripts for the Remote
    Control session script": `data/codebase/devcontainer/scripts.md` gains the
    pane script's row and anchors; `devcontainer` and
    `flow-devcontainer-lifecycle` re-digested; `stale-map-docs.py` ends
    `RESULT=SUCCESS`.

### Task 4: Verify in a live Coder workspace

- [x] With this change in a Coder workspace's checkout, record the
  claude.ai/code URL from
  `tmux -L claude-remote capture-pane -p -t claude-remote`, restart the
  workspace, and confirm that after restart the pane shows the same URL and the
  conversation's earlier turns, and that
  `cat ~/.claude/remote-control-session-id` is unchanged.
  - **Evidence:** live check on Coder workspace `agent-dev2`, template version
    `lingering_bell82`, Claude Code 2.1.296, 2026-10-13: with both scripts from
    commit "Start the Remote Control pane through the session script", a
    `coder restart` left the pane on the same claude.ai/code session URL,
    showing the conversation's earlier turn, under the unchanged stored ID; the
    `coder_script` started the pane through `claude-remote-control-session.sh`.

## Spec changes

[Claude Remote Control](../spec/claude-remote-control.md): the autostart
requirement, as restated by the plan this one depends on, gains the pinned
conversation and its fallback; its scenarios are carried over and three are
added.

``` markdown
## MODIFIED Requirements

### Requirement: Remote Control autostarts only on a live claude.ai login

`claude-remote-control-start.sh` SHALL start Remote Control in exactly one
detached tmux session named `claude-remote`, on the dedicated tmux server
`tmux -L claude-remote`, naming the Remote Control session after
`CODER_WORKSPACE_NAME` when it is set, only when `claude auth status --json`
reports `loggedIn: true` with `authMethod: "claude.ai"`. The Coder template's
`coder_script` on the dev container's sub-agent runs it on every agent start;
no devcontainer lifecycle hook runs it. Repeated or concurrent runs SHALL reuse
a live session rather than create another. It SHALL skip startup when `claude`
or `tmux` is unavailable. The Claude process SHALL NOT receive
`CLAUDE_CODE_OAUTH_TOKEN`.

The session SHALL resume the conversation whose ID is stored in
`remote-control-session-id` under Claude's configuration directory. When no ID
is stored, or the resume exits non-zero, it SHALL start a new conversation
under a newly generated ID and store that ID in place of the old one. A
transient failure to reconnect a resumed conversation leaves Claude running
with Remote Control off; running `/remote-control` in the session restores it.

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
- **THEN** claude.ai/code lists the Remote Control session under that
  workspace name.

#### Scenario: the workspace restarts or is rebuilt

- **WHEN** `claude-remote` starts with a stored conversation ID whose
  conversation still exists
- **THEN** it resumes that conversation, and claude.ai/code shows it under the
  same session URL with its earlier turns.

#### Scenario: the first start in a new volume

- **WHEN** `claude-remote` starts with no stored conversation ID
- **THEN** it starts a new conversation and stores its ID.

#### Scenario: the stored conversation cannot be resumed

- **WHEN** resuming the stored conversation exits non-zero
- **THEN** a new conversation starts under a new ID, and that ID replaces the
  stored one.
```

## Depends on

- [Start Claude Remote Control from the Coder
  agent](20261011-coder-claude-remote-control.md): its restated autostart
  requirement is the baseline this delta modifies.

## Verification

- `uv run pytest scripts/tests/test_claude_remote_control_start.py scripts/tests/test_claude_remote_control_session.py`
  green; `shellcheck` clean on both scripts.
- Task 4's live check: one restart of a Coder workspace keeps the same
  claude.ai/code session URL and history.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Detecting or recovering a transient reconnect failure; it stays a documented
  limitation.
- Checking for the transcript file before resuming.
- Resuming more than one conversation per volume, or sharing a conversation
  across devcontainer instances.
- Changes to the Coder template's `coder_script`.

## Key references

Verified anchor points (line numbers as of 2026-10-13):

- `.devcontainer/scripts/claude-remote-control-start.sh:29-35` — `session`,
  `workspace`, `pane_command` running `claude-remote-control-session.sh` with
  the optional `CODER_WORKSPACE_NAME` name
- `.devcontainer/scripts/claude-remote-control-start.sh:42-44` — `tmux_start`,
  the pane command with `env -u CLAUDE_CODE_OAUTH_TOKEN`
- `.devcontainer/scripts/claude-remote-control-session.sh:5` — `id_file`, the
  stored conversation ID
- `.devcontainer/devcontainer.json:83-84` — the `agentdev-claude` volume mounted
  at `/root/.claude`
- `scripts/tests/test_claude_remote_control_start.py:33` — `run_with_fake_tmux`
- `scripts/tests/test_claude_remote_control_start.py:84` —
  `test_names_session_after_coder_workspace`
- `scripts/tests/test_claude_remote_control_start.py:128` —
  `test_real_tmux_starts_claude_without_setup_token`, whose fake `claude`
  requires `--remote-control` as its first argument
