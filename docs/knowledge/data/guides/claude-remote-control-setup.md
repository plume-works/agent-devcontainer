---
type: guide
description: How to set up Claude Remote Control on a Coder workspace or the standalone runtime, and how to diagnose a Login expired state.
sources:
- resource: py_packages/agentdev_runtime/
---

# Claude Remote Control setup

The behaviour this procedure relies on is in the [Claude Remote Control
spec](../spec/claude-remote-control.md).

## Set it up

### 1. Attach the Coder agent start, or opt in the standalone runtime

On Coder, the workspace template's `coder_script` on the dev container's
sub-agent runs the repository's agent-start command, by default
`agentdev-runtime coder start`, on every agent start, and that command execs
`agentdev-runtime remote-control start` ([Devcontainer Git
credentials](../spec/devcontainer-git-credentials.md)). The `coder_script` runs
nothing when the repository ships no agent-start command ([Coder IDE
baseline](../spec/coder-ide-baseline.md)).

In the standalone `agentdev-deploy` runtime, set `AGENTDEV_CLAUDE_RC_MODE` to
`session` or `server` (and, in server mode, optionally
`AGENTDEV_CLAUDE_RC_SPAWN`); its `remote-control` watcher then runs
`agentdev-runtime remote-control start` once a claude.ai login exists, and
`agentdev-runtime health status` reports what it is doing. On other hosts
nothing starts Remote Control; the command can still be run by hand.

### 2. Log in

Run `claude` inside the container and complete `/login` with a claude.ai
account. The login persists in the shared volume, so later workspaces on the
same host start Remote Control on their next agent start. In the workspace where
the login happened, start it by hand from a Coder terminal, which carries the
same environment as the `coder_script`:

``` bash
agentdev-runtime remote-control start
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
  /var/lib/agentdev/auth/claude \
  /var/lib/agentdev/auth/claude/.credentials.json

claude auth status --json

tmux -L claude-remote list-sessions -F '#{session_name}'
tmux -L claude-remote list-panes -t =claude-remote \
  -F 'session=#{session_name} dead=#{pane_dead} command=#{pane_current_command}'
```

Expected filesystem metadata is ownership by the runtime account, mode `0700` on
the credential directory, and mode `0600` on the credential file. Exactly one
tmux session named `claude-remote` on the `claude-remote` tmux server should
contain one live `claude` pane.

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
