---
type: spec
description: Claude Remote Control autostarts from the Coder agent only on a live claude.ai login, inheriting the agent's environment and either resuming its pinned conversation or, opted in with AGENTDEV_CLAUDE_RC_MODE=server, running a spawn-on-demand server, and every container pre-approves Claude's first-run state unless it opts out.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-24T03:00:00Z
sources:
- resource: .devcontainer/docker-compose.yml
- resource: .devcontainer/scripts/claude-remote-control-pin.sh
- resource: .devcontainer/scripts/claude-remote-control-session.sh
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: .devcontainer/scripts/coder-agent-start.sh
- resource: .devcontainer/scripts/preapprove-claude-workspace.sh
- resource: .devcontainer/scripts/postCreateCommand.sh
- resource: .devcontainer/scripts/postStartCommand.sh
- resource: .github/actions/run-claude-responder/action.yml
- resource: scripts/tests/test_claude_remote_control_pin.py
- resource: scripts/tests/test_claude_remote_control_session.py
- resource: scripts/tests/test_claude_remote_control_start.py
- resource: scripts/tests/test_preapprove_claude_workspace.py
- resource: https://code.claude.com/docs/en/errors#login-expired
- resource: https://code.claude.com/docs/en/authentication
- resource: https://code.claude.com/docs/en/remote-control
- resource: https://github.com/anthropics/claude-code/issues/21765
- resource: https://github.com/anthropics/claude-code/issues/88583
- resource: https://github.com/plume-works/coder-ide-baseline/blob/ab1c595/template/main.tf
- resource: https://coder.com/docs/v2.37/user-guides/user-secrets
---

# Claude Remote Control

Claude credentials come only from a `/login` inside a container, persisted in
the shared `agentdev-agents-auth` volume ([Agent auth
persistence](../architecture/agent-auth-persistence.md)). On top of that login,
a Coder workspace starts Claude Remote Control unattended under the Coder agent,
and every devcontainer answers Claude's first-run prompts ahead of time.

## Requirements

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

### Requirement: server mode is opt-in

`AGENTDEV_CLAUDE_RC_MODE` SHALL select the mode: `server` selects server mode,
and an unset or `session` value selects session mode. Any other value SHALL make
the script print the value and the valid options to stderr, start no session,
and exit non-zero, before any other check. In server mode the `claude-remote`
session SHALL run `claude remote-control --spawn same-dir`, passing `--name` and
`--remote-control-session-name-prefix` set to `CODER_WORKSPACE_NAME` when it is
set, and SHALL neither read nor write the stored conversation ID.

#### Scenario: server mode is selected

- **WHEN** the script starts `claude-remote` with
  `AGENTDEV_CLAUDE_RC_MODE=server`
- **THEN** the session runs `claude remote-control --spawn same-dir` and reaches
  a connected server with no terminal interaction.

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

### Requirement: Remote Control inherits the Coder agent's environment

The Claude process in `claude-remote` SHALL receive the environment of the
process that ran `claude-remote-control-start.sh`, including when another tmux
server is live on the default socket. Started by the `coder_script`, it SHALL
carry the Coder user secrets and the agent's git credential helper.

#### Scenario: a GitHub token is a Coder user secret

- **WHEN** the workspace owner has a `GITHUB_TOKEN` env user secret and the
  `coder_script` starts `claude-remote`
- **THEN** `gh auth status` succeeds from the Remote Control session.

#### Scenario: a default tmux server is already running

- **WHEN** a tmux server is live on the default socket before the script runs
- **THEN** `claude-remote` starts on its own server and its Claude process
  receives the script's environment.

### Requirement: every container pre-approves first-run Claude state

Unless `AGENTDEV_SKIP_CLAUDE_PREAPPROVE` is non-empty, post-create SHALL record
in Claude's state file (`~/.claude.json`, written through its symlink into the
persistent volume) that onboarding is complete, the Remote Control confirmation
was seen, and the workspace is trusted. It SHALL set
`enableAllProjectMcpServers` in the workspace's `.claude/settings.local.json`
and SHALL keep any existing `disabledMcpjsonServers` list. Existing keys in both
files SHALL be preserved. The CI responder SHALL set the opt-out.

#### Scenario: a new workspace autostarts Remote Control

- **WHEN** a Coder workspace is created on a template whose `coder_script`
  starts Remote Control, with a valid claude.ai login in the shared volume
- **THEN** `claude-remote` reaches `/rc active` with no terminal interaction and
  every project `.mcp.json` server enabled except those listed in
  `disabledMcpjsonServers`.

#### Scenario: Remote Control is not started

- **WHEN** a container is created where nothing starts Remote Control
- **THEN** the first interactive `claude` session shows no onboarding, trust, or
  project-MCP prompt.

#### Scenario: the CI responder runs the lifecycle scripts

- **WHEN** `postCreateCommand.sh` runs with `AGENTDEV_SKIP_CLAUDE_PREAPPROVE`
  set
- **THEN** neither `~/.claude.json` nor `.claude/settings.local.json` is
  modified.

## Setup procedure

### 1. Attach the Coder agent start

Autostart is Coder-only. The workspace template's `coder_script` on the dev
container's sub-agent runs the repository's agent-start script, by default
`.devcontainer/scripts/coder-agent-start.sh`, on every agent start, and that
script execs `claude-remote-control-start.sh` ([Devcontainer Git
credentials](devcontainer-git-credentials.md)). The `coder_script` runs nothing
when the repository ships no such script. On other hosts nothing starts Remote
Control; the script can still be run by hand.

### 2. Log in

Run `claude` inside the container and complete `/login` with a claude.ai
account. The login persists in the shared volume, so later workspaces on the
same host start Remote Control on their next agent start. In the workspace where
the login happened, start it by hand from a Coder terminal, which carries the
same environment as the `coder_script`:

``` bash
.devcontainer/scripts/claude-remote-control-start.sh
```

A workspace restart also starts it.

### 3. Approve first-run Claude state

Post-create has already answered these prompts. Attach to the named tmux session
only if Claude still shows one, for example after a Claude Code release adds a
new first-run prompt:

``` bash
tmux -L claude-remote attach -t claude-remote
```

Complete only the prompts that are actually shown:

1. Claude Code onboarding, if the persistent Claude state is new.
2. Workspace trust for the opened repository.
3. MCP server selection; enable only servers intended for that workspace.
4. **Enable Remote Control** when `/remote-control` asks for approval.

Authentication, onboarding, workspace trust, MCP selection, and Remote Control
authorization are separate states. Record them in Claude's state files, never
with blind keystrokes into the session. A ready session displays `/rc active`
and directs the operator to `claude.ai/code` or the Code tab in the Claude
mobile app.

### 4. Verify without exposing credentials

Run the following checks inside the nested container. They inspect metadata and
boolean authentication state, not credential values:

``` bash
stat -c '%U %a %n' \
  /root/.agents-auth/claude \
  /root/.agents-auth/claude/.credentials.json

claude auth status --json

tmux -L claude-remote list-sessions -F '#{session_name}'
tmux -L claude-remote list-panes -t =claude-remote \
  -F 'session=#{session_name} dead=#{pane_dead} command=#{pane_current_command}'
```

Expected filesystem metadata is root ownership, mode `0700` on the credential
directory, and mode `0600` on the credential file. Exactly one tmux session
named `claude-remote` on the `claude-remote` tmux server should contain one live
`claude` pane.

To verify that native file authentication took precedence, inspect only the
environment variable names of the Claude process and assert that
`CLAUDE_CODE_OAUTH_TOKEN` is absent. Never dump the complete process
environment.

## Diagnose `Login expired`

Anthropic defines `Login expired · Please run /login` as a local terminal state:
Claude Code tried to renew the saved login, the OAuth service rejected the
stored refresh token, and Claude Code cleared the saved credentials. Later
requests stop locally rather than reaching the API. This differs from an API
response that reports a revoked or expired access token.

The cleared Linux credential retains its non-secret account metadata but has
this diagnostic shape:

``` text
claudeAiOauth.accessToken:           empty
claudeAiOauth.refreshToken:          empty
claudeAiOauth.expiresAt:             0
claudeAiOauth.refreshTokenExpiresAt: may remain in the future
claude auth status:                  loggedIn=false
```

Inspect only field presence, emptiness, expiry metadata, file timestamps, and
`claude auth status --json`; never print token values. A future
`refreshTokenExpiresAt` does not make an empty or rejected refresh token usable.

Correlate the credential file modification time with other refresh owners. A
credential rotating in one client immediately before another copy is cleared is
evidence of refresh-token divergence. The same signature is reported upstream
when concurrent Claude clients race a single-use refresh token: the losing
client persists empty token fields and `expiresAt: 0`.

The cleared credential document is still a non-empty file, so a healthy JSON
parse and mode `0600` prove storage integrity, not authentication health. Run
`/login` again to recover.
