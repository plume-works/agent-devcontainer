---
type: spec
description: The Coder agent start runs the OpenCode v2 server and web UI in a reusable tmux session on port 4096, always behind a server password and bound beyond localhost only with a configured one, prints the server's root URL, and keeps logins and chats per worktree across rebuilds.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T20:55:00Z
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/opencode.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/coder.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: .devcontainer/devcontainer.json
- resource: scripts/tests/test_opencode_web_start.py
- resource: scripts/tests/test_coder_agent_start.py
---

# OpenCode web

The OpenCode web UI server that the Coder agent start runs in every Dev
Container. Credentials and per-instance state follow [Agent auth
persistence](../architecture/agent-auth-persistence.md); the dashboard app that
opens the server is part of the [Coder IDE baseline
template](coder-ide-baseline.md).

## Requirements

### Requirement: the Coder agent start runs the OpenCode web UI

`agentdev-runtime coder start` SHALL run `agentdev-runtime opencode coder-start`
on every agent start, before Remote Control starts. The command SHALL start
`opencode serve` in exactly one detached tmux session named `opencode` on the
dedicated tmux server `tmux -L opencode`, in the workspace folder, without
checking for a provider login. Repeated runs SHALL reuse a live session. It
SHALL skip startup when `opencode` or `tmux` is unavailable. A failure SHALL NOT
stop Remote Control from starting. On a start or a reuse it SHALL print the
server's root URL, `VSCODE_PROXY_URI` with `{{port}}` replaced by `4096` and any
trailing `/` removed, or `http://127.0.0.1:4096` when `VSCODE_PROXY_URI` is
unset or empty.

#### Scenario: a workspace starts

- **WHEN** the Coder agent starts and no `opencode` session is live
- **THEN** `opencode serve` runs in the `opencode` session on
  `tmux -L opencode`.

#### Scenario: the agent start runs again

- **WHEN** the `opencode` session is already live
- **THEN** no second session or server starts.

#### Scenario: the start prints the server's URL

- **WHEN** the command starts or reuses the `opencode` session
- **THEN** its output carries Coder's port URL for 4096, which opens the web UI
  through Coder.

#### Scenario: the start runs outside Coder

- **WHEN** `VSCODE_PROXY_URI` is unset
- **THEN** the printed link is `http://127.0.0.1:4096`.

#### Scenario: the OpenCode start fails

- **WHEN** `agentdev-runtime opencode coder-start` exits non-zero
- **THEN** the agent start warns and Remote Control still starts.

### Requirement: the server is exposed only behind a password

The server SHALL listen on port 4096 and SHALL always require a password. When
`OPENCODE_SERVER_PASSWORD` is non-empty in the agent's environment, the server
SHALL use it and bind `0.0.0.0`. Otherwise it SHALL bind `127.0.0.1` and use the
password in `~/.local/share/opencode/agentdev-server-password`, which the
command SHALL create with a random value and mode `0600` when it is missing. The
password SHALL NOT appear in the command's output or the server's command line;
the output SHALL name the password file when that file is in use.

#### Scenario: no password is set

- **WHEN** `OPENCODE_SERVER_PASSWORD` is unset or empty
- **THEN** the server listens on `127.0.0.1:4096` only, rejects a request
  without the password from the password file, and the output names that file.

#### Scenario: the workspace starts again without a password

- **WHEN** the password file already exists and `OPENCODE_SERVER_PASSWORD` is
  unset
- **THEN** the server uses the existing password.

#### Scenario: a password is set

- **WHEN** `OPENCODE_SERVER_PASSWORD` is non-empty
- **THEN** the server listens on `0.0.0.0:4096` and rejects a request without
  that password.

### Requirement: OpenCode logins and chats survive a rebuild

`~/.local/share/opencode`, which holds OpenCode's provider logins, sessions, and
the generated server password, SHALL live on the per-instance
`agentdev-opencode` volume.

#### Scenario: a provider is connected and the container is rebuilt

- **WHEN** a provider is connected from the web UI's Settings and the Dev
  Container is rebuilt
- **THEN** the provider is still connected and earlier sessions are listed.

#### Scenario: a second worktree starts

- **WHEN** another worktree's Dev Container starts on the same host
- **THEN** it sees none of the first worktree's provider logins or sessions.
