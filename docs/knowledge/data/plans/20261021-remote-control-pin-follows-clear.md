---
type: plan
created: 2026-10-21
release:
- bugs/remote-control-pin-ignores-clear
description: Keep the claude-remote pane's pinned conversation ID on the conversation the pane is running, through a SessionStart hook supplied only to the pane, so a workspace restart after /clear resumes the post-clear conversation under the same claude.ai session URL.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-21T01:50:00Z
sources:
- resource: .devcontainer/scripts/claude-remote-control-session.sh
- resource: scripts/tests/test_claude_remote_control_session.py
- resource: https://code.claude.com/docs/en/hooks
---

# Keep the Remote Control pin on the pane's current conversation

## Context

[Bug: the Remote Control pin ignores
`/clear`](../bugs/remote-control-pin-ignores-clear.md):
`claude-remote-control-session.sh` writes `remote-control-session-id` only
before it launches Claude, so `/clear` in the pane leaves the pin on the
pre-clear conversation. The next workspace restart resumes that conversation,
whose remote binding `/clear` already moved away, and Claude Code mints a new
claude.ai session URL for it. [Claude Remote Control
resume](../architecture/claude-remote-control-resume.md) records the pinning
decision this plan extends.

## Approach

The pane's Claude process gets a `SessionStart` hook through
`claude --settings`, and only that process: `claude-remote-control-session.sh`
passes the same `--settings` value on the resume call and on the fresh
`--session-id` call. The hook runs a new script, `claude-remote-control-pin.sh`,
which reads the hook's JSON input from stdin and writes its `session_id` to
`${CLAUDE_CONFIG_DIR:-$HOME/.claude}/remote-control-session-id` through a
temporary file in the same directory and `mv`, so a reboot during the write
cannot leave a truncated ID. An empty or missing `session_id`, or input that
does not parse, leaves the pin unchanged, writes a message to stderr, and exits
0, so the hook never disturbs the session. The existing resume and fallback
logic is unchanged.

`SessionStart` fires with `source` `startup`, `resume`, `clear`, and `compact`;
on `startup`, `resume`, and `compact` the hook rewrites the ID already pinned,
which is harmless. The hook reads the pin path from the inherited
`CLAUDE_CONFIG_DIR` the same way the session script does, so the `--settings`
value carries only the hook command. The session script builds that JSON with
`jq -n --arg` from the `printf '%q'`-quoted pin script path, so the path is both
shell- and JSON-safe; the pin script parses its input with `jq`.

Rejected: a hook in the repository's `.claude/settings.json` gated on an
environment variable the session script exports, because every Claude session in
the repository would run it; and choosing the newest transcript at boot, because
it depends on Claude Code's undocumented transcript layout and can select an
operator's terminal session.

## Implementation Steps

### Task 1: Pin script writes the hook's session ID

**Files:** Create: `.devcontainer/scripts/claude-remote-control-pin.sh`,
`scripts/tests/test_claude_remote_control_pin.py`

- [x] Tests first; every test points `CLAUDE_CONFIG_DIR` at a directory under
  `./.tmp`, never the real `~/.claude`:
  - stdin `{"session_id": "<uuid>", "source": "clear"}` with an existing pin:
    the pin holds `<uuid>`, the script exits 0, and no temporary file remains in
    the directory;
  - the same input with no pin file and no config directory: the directory and
    pin are created holding `<uuid>`;
  - stdin with `session_id` empty, stdin without `session_id`, and stdin that is
    not JSON: each exits 0 with the pin unchanged.
  - **Evidence:** commit "Add the Remote Control pin hook script":
    `test_claude_remote_control_pin.py`, one test per case; all five failed
    before the script existed.
- [x] Script: `#!/usr/bin/env bash`, `set -euo pipefail`, behavior as in
  `## Approach`.
  - **Evidence:** commit "Add the Remote Control pin hook script":
    `claude-remote-control-pin.sh`.
- [x] `shellcheck` clean;
  `uv run pytest scripts/tests/test_claude_remote_control_pin.py` green.
  - **Evidence:** commit "Add the Remote Control pin hook script": `shellcheck`
    clean; the test file 5 passed.

### Task 2: Session script supplies the hook to the pane

**Files:** Modify: `.devcontainer/scripts/claude-remote-control-session.sh`,
`scripts/tests/test_claude_remote_control_session.py`

- [ ] Tests first: the four existing tests keep their call sequence and pin
  assertions with `--settings <json>` added to every call; a new test parses
  that JSON and asserts one `SessionStart` command hook whose command runs
  `claude-remote-control-pin.sh` from the script's directory, identical on the
  resume and the fallback `--session-id` call.
- [ ] Script: build the `--settings` value once and pass it on both `claude`
  invocations.
- [ ] `shellcheck` clean;
  `uv run pytest scripts/tests/test_claude_remote_control_session.py scripts/tests/test_claude_remote_control_start.py`
  green.

### Task 3: Record the hook decision

**Files:** Modify:
`docs/knowledge/data/architecture/claude-remote-control-resume.md`

- [ ] `## Decision` gains that the pane's `SessionStart` hook, supplied through
  `--settings`, rewrites the stored ID whenever the pane's conversation changes.
  `## Claude Code behavior the decision relies on` gains, measured on Claude
  Code 2.1.304 in interactive `--remote-control` mode: a hook supplied through
  `--settings` fires with `source` `startup`, `clear`, and `resume`; on `clear`
  its `session_id` is the new conversation's ID and the pre-clear transcript's
  binding is emptied; resuming the ID the hook recorded reattaches the original
  claude.ai session URL. `## Rejected alternatives` gains the two alternatives
  rejected in `## Approach`. `sources` gains
  `https://code.claude.com/docs/en/hooks` and both scripts; `generated` is
  restamped.
- [ ] `iwe normalize` and `iwe schema validate` pass.

### Task 4: The pin follows `/clear` in a Coder workspace

**Files:** none

- [ ] On a Coder workspace running the change: note the claude.ai session URL,
  run `/clear` in `claude-remote` and send a prompt, confirm
  `remote-control-session-id` now holds the post-clear conversation's ID,
  restart the workspace, and confirm the pane resumes the post-clear
  conversation under the noted URL.

## Spec changes

[Claude Remote Control](../spec/claude-remote-control.md): the stored ID follows
an in-process conversation change, which adds a scenario to the autostart
requirement.

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

The session SHALL resume the conversation whose ID is stored in
`remote-control-session-id` under Claude's configuration directory. When no ID
is stored, or the resume exits non-zero, it SHALL start a new conversation under
a newly generated ID and store that ID in place of the old one. Whenever the
session's conversation changes while Claude runs, including through `/clear`,
the session SHALL store the new conversation's ID in place of the old one; no
other Claude process SHALL write the stored ID. A transient failure to
reconnect a resumed conversation leaves Claude running with Remote Control off;
running `/remote-control` in the session restores it.

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

#### Scenario: the operator clears the conversation

- **WHEN** `/clear` runs in `claude-remote` and the workspace then restarts
- **THEN** the pane resumes the post-clear conversation under the same session
  URL.
```

## Verification

- `shellcheck .devcontainer/scripts/claude-remote-control-pin.sh .devcontainer/scripts/claude-remote-control-session.sh`
  is clean.
- `uv run pytest scripts/tests/test_claude_remote_control_pin.py scripts/tests/test_claude_remote_control_session.py scripts/tests/test_claude_remote_control_start.py`
  passes.
- `iwe normalize` and `iwe schema validate` pass.
- Task 4's workspace check passes.

## Out of scope

- Repairing a pin that is already stale when the change deploys: the first start
  after deployment resumes the stored conversation and the hook pins that same
  ID. Pointing the pin at a later conversation is a one-time manual rewrite of
  `remote-control-session-id`.
- `/resume` of another conversation inside the pane is covered only through
  Claude Code's documented `source: "resume"`; the plan does not measure it.
- Health checks for a pane whose Remote Control is off, which [Claude Remote
  Control resume](../architecture/claude-remote-control-resume.md) already
  rejects.

## Key references

Verified anchor points (line numbers as of 2026-10-21):

- `.devcontainer/scripts/claude-remote-control-session.sh:5` — `id_file`, the
  pin path.
- `.devcontainer/scripts/claude-remote-control-session.sh:15` — the resume of
  the stored ID.
- `.devcontainer/scripts/claude-remote-control-session.sh:21` — the pin write
  before the fresh start.
- `.devcontainer/scripts/claude-remote-control-session.sh:22` — `exec claude`
  with `--session-id`.
- `scripts/tests/test_claude_remote_control_session.py:14` — `FAKE_CLAUDE`, the
  argument-logging fake.
- `scripts/tests/test_claude_remote_control_session.py:29` — `run_session`.
- `docs/knowledge/data/spec/claude-remote-control.md:37` — Requirement: Remote
  Control autostarts only on a live claude.ai login.
- `docs/knowledge/data/architecture/claude-remote-control-resume.md:15` —
  `## Decision`.
- `docs/knowledge/data/architecture/claude-remote-control-resume.md:48` —
  `## Rejected alternatives`.
