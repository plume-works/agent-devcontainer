---
type: spec
description: The Coder agent start runs the OpenCode web UI in a reusable tmux session on port 4096, bound beyond localhost only behind a server password, prints a link into the workspace folder, and keeps logins shared and chats per worktree across rebuilds.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-17T12:00:00Z
sources:
- resource: .devcontainer/scripts/opencode-web-start.sh
- resource: .devcontainer/scripts/coder-agent-start.sh
- resource: .devcontainer/scripts/link-opencode-auth.sh
- resource: .devcontainer/scripts/postCreateCommand.sh
- resource: .devcontainer/scripts/postStartCommand.sh
- resource: .devcontainer/devcontainer.json
- resource: scripts/tests/test_opencode_web_start.py
- resource: scripts/tests/test_coder_agent_start.py
- resource: scripts/tests/test_link_opencode_auth.py
---

# OpenCode web

The OpenCode web UI server that the Coder agent start runs in every Dev
Container. Credentials and per-instance state follow [Agent auth
persistence](../architecture/agent-auth-persistence.md); the dashboard app that
opens the server is part of the [Coder IDE baseline
template](coder-ide-baseline.md).

## Requirements

### Requirement: the Coder agent start runs the OpenCode web UI

`coder-agent-start.sh` SHALL run `opencode-web-start.sh` on every agent start,
before Remote Control starts. The script SHALL start `opencode web` in exactly
one detached tmux session named `opencode` on the dedicated tmux server
`tmux -L opencode`, in the workspace folder, without checking for a provider
login. Repeated runs SHALL reuse a live session. It SHALL skip startup when
`opencode` or `tmux` is unavailable. A failure SHALL NOT stop Remote Control
from starting. On a start or a reuse it SHALL print
`<base>/<base64url(workspace folder)>/session`, base64url without `=` padding,
where `<base>` is `VSCODE_PROXY_URI` with `{{port}}` replaced by `4096` and any
trailing `/` removed, or `http://127.0.0.1:4096` when `VSCODE_PROXY_URI` is
unset or empty.

#### Scenario: a workspace starts

- **WHEN** the Coder agent starts and no `opencode` session is live
- **THEN** `opencode web` runs in the `opencode` session on `tmux -L opencode`.

#### Scenario: the agent start runs again

- **WHEN** the `opencode` session is already live
- **THEN** no second session or server starts.

#### Scenario: the start prints a link into the workspace folder

- **WHEN** the script starts or reuses the `opencode` session
- **THEN** its output carries the link built on Coder's port URL for 4096, which
  opens a session in the workspace folder through Coder.

#### Scenario: the start runs outside Coder

- **WHEN** `VSCODE_PROXY_URI` is unset
- **THEN** the printed link starts with `http://127.0.0.1:4096`.

#### Scenario: the OpenCode start fails

- **WHEN** `opencode-web-start.sh` exits non-zero
- **THEN** the agent start warns and Remote Control still starts.

### Requirement: the server is exposed only behind a password

The server SHALL listen on port 4096. It SHALL bind `0.0.0.0` only when
`OPENCODE_SERVER_PASSWORD` is non-empty in the agent's environment, and
`127.0.0.1` otherwise.

#### Scenario: no password is set

- **WHEN** `OPENCODE_SERVER_PASSWORD` is unset or empty
- **THEN** the server listens on `127.0.0.1:4096` only.

#### Scenario: a password is set

- **WHEN** `OPENCODE_SERVER_PASSWORD` is non-empty
- **THEN** the server listens on `0.0.0.0:4096` and rejects a request without
  the password.

### Requirement: OpenCode logins and chats survive a rebuild

`~/.local/share/opencode/auth.json` SHALL be a symlink to
`/root/.agents-auth/opencode/auth.json`, restored on every container create and
start, with a pre-existing regular file moved to the target first. The rest of
`~/.local/share/opencode` SHALL live on the per-instance `agentdev-opencode`
volume.

#### Scenario: a provider is connected and the container is rebuilt

- **WHEN** a provider is connected from the web UI's Settings and the Dev
  Container is rebuilt
- **THEN** the provider is still connected and earlier sessions are listed.

#### Scenario: a second worktree starts

- **WHEN** another worktree's Dev Container starts on the same host
- **THEN** it sees the same provider logins and none of the first worktree's
  sessions.
