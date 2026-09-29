---
type: spec
description: Securely seed native Claude and Codex credentials, propagate Git identity, and start Claude Remote Control in a Coder-backed devcontainer.
generated:
  by: hermes-agent/gpt-5.6
  at: 2026-09-29T07:48:22+00:00
sources:
- resource: .devcontainer/devcontainer-init.sh
- resource: .devcontainer/docker-compose.yml
- resource: .devcontainer/scripts/prepare-agent-auth-seed.sh
- resource: .devcontainer/scripts/seed-agent-auth.sh
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: .devcontainer/scripts/postCreateCommand.sh
- resource: .devcontainer/scripts/postStartCommand.sh
- resource: .devcontainer/scripts/setup-gh-credential-helper.sh
- resource: .devcontainer/scripts/preapprove-claude-workspace.sh
- resource: https://code.claude.com/docs/en/errors#login-expired
- resource: https://code.claude.com/docs/en/authentication
- resource: https://github.com/anthropics/claude-code/issues/21765
- resource: https://github.com/anthropics/claude-code/issues/88583
---

# Devcontainer agent authentication and Claude Remote Control

Coder user secrets provide initial native authentication state and Git identity
to the outer workspace. The devcontainer lifecycle moves the authentication
state through private files rather than putting credential JSON in the resolved
Compose environment. Claude and Codex then use writable files in the shared
`agentdev-agents-auth` volume, allowing the CLIs to refresh their own tokens.
For Claude.ai OAuth, that writable state belongs to one refresh owner; copying
one snapshot into independently active workspaces does not create independent
logins.

## Requirements

### Requirement: native authentication enters through Coder user secrets

The outer Coder workspace SHALL receive complete native credential documents in
`AGENTDEV_CLAUDE_JSON` and `AGENTDEV_CODEX_JSON`. Claude Remote Control SHALL
use a native Claude.ai login file; `CLAUDE_CODE_OAUTH_TOKEN` is not a substitute
for Remote Control authentication.

#### Scenario: authentication is seeded into a new workspace

- **WHEN** the outer workspace starts with valid native Claude and Codex JSON
  secrets
- **THEN** the nested devcontainer receives private, writable native credential
  files without exposing either JSON document in its Compose environment.

### Requirement: initialization uses a private transfer directory

`devcontainer-init.sh` SHALL validate each configured seed as a JSON object and
materialize it under a workspace-specific transfer directory with mode `0700`.
Seed files SHALL have mode `0600`. Compose SHALL receive only the transfer path,
not credential values.

#### Scenario: Compose diagnostics are emitted

- **WHEN** Dev Containers prints the resolved Compose configuration during
  startup or failure
- **THEN** the output contains the private transfer path but no Claude or Codex
  credential JSON.

### Requirement: live credentials are seeded once

The post-create lifecycle SHALL install a seed only when its live target is
absent or empty. An existing non-empty target SHALL win because it may contain
newer state written by the CLI. Credential directories SHALL be mode `0700`,
credential files SHALL be mode `0600`, and consumed transfer files SHALL be
removed.

The live targets are:

- Claude: `/root/.agents-auth/claude/.credentials.json`
- Codex: `/root/.agents-auth/codex/auth.json`

#### Scenario: a CLI has refreshed its token

- **WHEN** a later container start finds a non-empty live credential and an
  older static seed
- **THEN** the live credential content is preserved and its mode is corrected to
  `0600`.

### Requirement: a Claude OAuth snapshot has one refresh owner

An operator SHALL NOT use one native Claude.ai OAuth credential snapshot as
durable authentication for multiple independently active workspaces. Claude.ai
rotates refresh tokens: after one consumer renews the login, another consumer
holding the previous snapshot can no longer rely on that refresh token.

Each independently refreshing workspace SHALL instead have an independent native
login, or all consumers SHALL use a single coordinated credential owner that
serializes refresh and atomically publishes the latest credential. A static
Coder secret is bootstrap material, not a credential broker or canonical
write-back store.

#### Scenario: two workspaces start from one snapshot

- **WHEN** two independently active Claude processes start with copies of the
  same access and refresh tokens
- **THEN** the setup treats expiry after either process refreshes as an expected
  credential-divergence risk, not as durable shared authentication.

#### Scenario: the source login rotates after the seed is captured

- **WHEN** the workspace that supplied a Coder seed refreshes its native login
  after the snapshot was captured
- **THEN** the static seed is considered potentially stale even if its JSON is
  structurally valid and its recorded refresh-token expiry remains in the
  future.

### Requirement: Remote Control is opt-in and idempotent

`AGENTDEV_CLAUDE_AUTOSTART=1` SHALL start `claude /remote-control` in exactly
one detached tmux session named `claude-remote`. Repeated or concurrent
lifecycle hooks SHALL reuse the live session rather than creating duplicates.
The launcher SHALL skip startup when authentication, `claude`, or `tmux` is
unavailable.

When native file authentication is available, the Claude process SHALL NOT
receive `CLAUDE_CODE_OAUTH_TOKEN`.

#### Scenario: the container restarts

- **WHEN** post-start runs while `claude-remote` is already live
- **THEN** it leaves the existing session running and creates no additional
  Claude process.

### Requirement: Git identity reaches the nested container

The outer workspace SHALL provide all four variables and Compose SHALL propagate
them into the nested container:

- `GIT_AUTHOR_NAME`
- `GIT_AUTHOR_EMAIL`
- `GIT_COMMITTER_NAME`
- `GIT_COMMITTER_EMAIL`

### Requirement: HTTPS git uses the gh login

When `gh` is authenticated to github.com and no git credential helper matches
`https://github.com`, post-start SHALL configure `gh` as the helper so git never
waits at an interactive credential prompt. An existing helper SHALL be kept.

### Requirement: autostart pre-approves first-run Claude state

When `AGENTDEV_CLAUDE_AUTOSTART=1`, post-create SHALL record in Claude's state
file (`~/.claude.json`, written through its symlink into the persistent volume)
that onboarding is complete, the Remote Control confirmation was seen, and the
workspace is trusted. It SHALL set `enableAllProjectMcpServers` and clear
`disabledMcpjsonServers` in the workspace's `.claude/settings.local.json`.
Existing keys in both files SHALL be preserved.

#### Scenario: a new workspace autostarts Remote Control

- **WHEN** a workspace is created with autostart enabled and valid Claude
  credentials
- **THEN** `claude-remote` reaches `/rc active` with no terminal interaction and
  every project `.mcp.json` server enabled.

## Setup procedure

### 1. Produce native credential files

Authenticate the official CLIs on a trusted machine or existing workspace and
verify their native files without printing them:

``` bash
claude auth status --json
codex login status
```

Use the complete files produced by those logins:

``` text
Claude: ~/.claude/.credentials.json
Codex:  ~/.codex/auth.json
```

A custom `CLAUDE_CONFIG_DIR` changes Claude's source path. Do not synthesize a
Claude credential document from a setup token, paste credential JSON into chat,
or place a credential value in command arguments.

### 2. Create the Coder user secrets

The Coder secret names are operator-chosen; the mapped environment names are the
contract. On first setup, create the secrets by streaming the files through
stdin:

``` bash
coder secret create agentdev-claude-json \
  --env AGENTDEV_CLAUDE_JSON < "$HOME/.claude/.credentials.json"

coder secret create agentdev-codex-json \
  --env AGENTDEV_CODEX_JSON < "$HOME/.codex/auth.json"

printf %s 1 | coder secret create agentdev-claude-autostart \
  --env AGENTDEV_CLAUDE_AUTOSTART
```

Use `coder secret update` with the same stdin redirection when rotating a seed.
A secret is only an initial seed: updating it does not overwrite a non-empty
live credential in an existing `agentdev-agents-auth` volume.

Create or update the four Git identity secrets in the same Coder account, mapped
to the exact `GIT_*` names listed above. Identity values are configuration, not
credentials, but they should still be supplied through Coder rather than baked
into the image.

### 3. Recreate the workspace

Coder injects user secrets when it creates the outer workspace container. Fully
restart or recreate the workspace after adding or changing secret mappings. A
nested-container restart alone does not refresh the outer environment.

During startup:

1. `devcontainer-init.sh` prepares private transfer files.
2. Compose bind-mounts the transfer directory at `/run/agentdev-auth-seed` and
   mounts `agentdev-agents-auth` at `/root/.agents-auth`.
3. `postCreateCommand.sh` seeds the live files, removes the transfer files, and
   pre-approves first-run Claude state when autostart is enabled.
4. `postStartCommand.sh` starts `claude /remote-control` when autostart is
   enabled.

### 4. Approve first-run Claude state

With autostart enabled, post-create has already answered these prompts. Attach
to the named tmux session only if Claude still shows one, for example after a
Claude Code release adds a new first-run prompt:

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

### 5. Verify without exposing credentials

Run the following checks inside the nested container. They inspect metadata and
boolean authentication state, not credential values:

``` bash
stat -c '%U %a %n' \
  /root/.agents-auth/claude \
  /root/.agents-auth/codex \
  /root/.agents-auth/claude/.credentials.json \
  /root/.agents-auth/codex/auth.json

python3 -m json.tool /root/.agents-auth/claude/.credentials.json >/dev/null
python3 -m json.tool /root/.agents-auth/codex/auth.json >/dev/null

claude auth status --json
codex login status

tmux list-sessions -F '#{session_name}'
tmux list-panes -t =claude-remote \
  -F 'session=#{session_name} dead=#{pane_dead} command=#{pane_current_command}'

for name in \
  GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL \
  GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL; do
  test -n "${!name:-}" || exit 1
done
```

Expected filesystem metadata is root ownership, mode `0700` on both credential
directories, and mode `0600` on both credential files. Exactly one tmux session
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
source credential rotating immediately before another copy is cleared is
evidence of refresh-token divergence. The same signature is reported upstream
when concurrent Claude clients race a single-use refresh token: the losing
client persists empty token fields and `expiresAt: 0`.

The seed-once lifecycle does not repair this state automatically. The cleared
credential document is still a non-empty file, so preserving it is consistent
with the rule that lifecycle startup never overwrites mutable live state. A
healthy JSON parse and mode `0600` therefore prove storage integrity, not
authentication health.

## Rotation and recovery

- Let Claude and Codex update their writable live files during normal token
  refresh. Do not repeatedly overwrite them from static Coder seeds.
- Capture a Claude Coder seed only for a bounded bootstrap into one refresh
  owner. Treat it as stale after that owner rotates the login; do not distribute
  the same snapshot to another independently active workspace.
- Updating a Coder secret does not update the environment of an already running
  outer workspace. Restarting only the nested container continues to expose the
  old seed environment.
- If a seed changes but an existing live file must be replaced, first establish
  that the live state is obsolete. Back it up only through an approved encrypted
  credential channel; plaintext credential backups are prohibited.
- A copied refresh-token snapshot is unsuitable as canonical authentication for
  multiple concurrently active disposable workspaces. Give each workspace an
  independent native login, or use a centralized single-owner refresh mechanism
  with atomic, versioned write-back when consumers must share rotating state.
- `CLAUDE_CODE_OAUTH_TOKEN` can authenticate model requests but cannot replace
  native login state for Remote Control, so it does not remove this constraint.
