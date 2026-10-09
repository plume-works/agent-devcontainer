---
type: spec
description: Claude Remote Control autostarts in a devcontainer only on a live claude.ai login, and every container pre-approves Claude's first-run state unless it opts out.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-09T00:00:00Z
sources:
- resource: .devcontainer/docker-compose.yml
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: .devcontainer/scripts/preapprove-claude-workspace.sh
- resource: .devcontainer/scripts/postCreateCommand.sh
- resource: .devcontainer/scripts/postStartCommand.sh
- resource: .github/actions/run-claude-responder/action.yml
- resource: scripts/tests/test_claude_remote_control_start.py
- resource: scripts/tests/test_preapprove_claude_workspace.py
- resource: https://code.claude.com/docs/en/errors#login-expired
- resource: https://code.claude.com/docs/en/authentication
- resource: https://github.com/anthropics/claude-code/issues/21765
- resource: https://github.com/anthropics/claude-code/issues/88583
---

# Claude Remote Control

Claude credentials come only from a `/login` inside a container, persisted in
the shared `agentdev-agents-auth` volume ([Agent auth
persistence](../architecture/agent-auth-persistence.md)). On top of that login,
the devcontainer can start Claude Remote Control unattended and answers Claude's
first-run prompts ahead of time.

## Requirements

### Requirement: Remote Control autostarts only on a live claude.ai login

`claude-remote-control-start.sh` SHALL start `claude /remote-control` in exactly
one detached tmux session named `claude-remote` only when
`AGENTDEV_CLAUDE_AUTOSTART=1` and `claude auth status --json` reports
`loggedIn: true` with `authMethod: "claude.ai"`. It runs from
`postStartCommand.sh` and may be run by hand. Repeated or concurrent runs SHALL
reuse a live session rather than create another. It SHALL skip startup when
`claude` or `tmux` is unavailable. The Claude process SHALL NOT receive
`CLAUDE_CODE_OAUTH_TOKEN`.

#### Scenario: the container restarts

- **WHEN** post-start runs while `claude-remote` is already live
- **THEN** it leaves the existing session running and creates no additional
  Claude process.

#### Scenario: the saved login has expired

- **WHEN** autostart is enabled and the credential file exists but
  `claude auth status --json` reports `loggedIn: false`
- **THEN** no session is started and the script exits successfully.

#### Scenario: only a setup token is available

- **WHEN** `claude auth status --json` reports `loggedIn: true` with an
  `authMethod` other than `claude.ai`
- **THEN** no session is started.

#### Scenario: the operator logs in after the container started

- **WHEN** an operator completes `/login` and runs the script by hand
- **THEN** `claude-remote` starts without a container restart.

### Requirement: every container pre-approves first-run Claude state

Unless `AGENTDEV_SKIP_CLAUDE_PREAPPROVE` is non-empty, post-create SHALL record
in Claude's state file (`~/.claude.json`, written through its symlink into the
persistent volume) that onboarding is complete, the Remote Control confirmation
was seen, and the workspace is trusted. It SHALL set
`enableAllProjectMcpServers` in the workspace's `.claude/settings.local.json`
and SHALL keep any existing `disabledMcpjsonServers` list. Existing keys in both
files SHALL be preserved. The CI responder SHALL set the opt-out.

#### Scenario: a new workspace autostarts Remote Control

- **WHEN** a workspace is created with autostart enabled and a valid claude.ai
  login in the shared volume
- **THEN** `claude-remote` reaches `/rc active` with no terminal interaction and
  every project `.mcp.json` server enabled except those listed in
  `disabledMcpjsonServers`.

#### Scenario: autostart is not enabled

- **WHEN** a workspace is created without `AGENTDEV_CLAUDE_AUTOSTART`
- **THEN** the first interactive `claude` session shows no onboarding, trust, or
  project-MCP prompt.

#### Scenario: the CI responder runs the lifecycle scripts

- **WHEN** `postCreateCommand.sh` runs with `AGENTDEV_SKIP_CLAUDE_PREAPPROVE`
  set
- **THEN** neither `~/.claude.json` nor `.claude/settings.local.json` is
  modified.

## Setup procedure

### 1. Enable autostart

Compose passes `AGENTDEV_CLAUDE_AUTOSTART` from the outer workspace. In Coder,
supply it as a user secret:

``` bash
printf %s 1 | coder secret create agentdev-claude-autostart \
  --env AGENTDEV_CLAUDE_AUTOSTART
```

Coder injects user secrets when it creates the outer workspace container, so
restart or recreate the workspace after adding the mapping.

### 2. Log in

Run `claude` inside the container and complete `/login` with a claude.ai
account. The login persists in the shared volume, so later containers on the
same host start Remote Control on their own. In the container where the login
happened, start it by hand:

``` bash
.devcontainer/scripts/claude-remote-control-start.sh
```

### 3. Approve first-run Claude state

Post-create has already answered these prompts. Attach to the named tmux session
only if Claude still shows one, for example after a Claude Code release adds a
new first-run prompt:

``` bash
tmux attach -t claude-remote
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

tmux list-sessions -F '#{session_name}'
tmux list-panes -t =claude-remote \
  -F 'session=#{session_name} dead=#{pane_dead} command=#{pane_current_command}'
```

Expected filesystem metadata is root ownership, mode `0700` on the credential
directory, and mode `0600` on the credential file. Exactly one tmux session
named `claude-remote` should contain one live `claude` pane.

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
