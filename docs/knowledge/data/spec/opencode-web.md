---
type: spec
description: The Coder agent start runs the OpenCode v2 server and web UI in a reusable tmux session on port 4096, always behind a server password and bound beyond localhost only with a configured one, prints the server's root URL, and keeps logins and chats per worktree across rebuilds.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/opencode.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/coder.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: .devcontainer/devcontainer.json
- resource: scripts/tests/test_opencode_web_start.py
- resource: scripts/tests/test_coder_agent_start.py
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: .devcontainer/docker-compose.yml
- resource: py_packages/agentdev_runtime/agentdev_runtime/settings.py
---

# OpenCode web

The OpenCode web UI server that the Coder agent start runs in every Dev
Container. Credentials and per-instance state follow [Devcontainer
state](devcontainer-state.md); the dashboard app that opens the server is part
of the `coder-ide-baseline` template's
[`spec/workspace-template`](https://github.com/plume-works/coder-ide-baseline/blob/main/docs/knowledge/data/spec/workspace-template.md).

## Requirements

### Requirement: OpenCode logins and chats survive a rebuild

`~/.local/share/opencode`, which holds OpenCode's database of provider logins
and sessions and the generated server password, SHALL live at that default path
on the runtime account's per-instance home volume,
`agentdev-home-${devcontainerId}` mounted at `/home/agent`, and on no volume of
its own.

#### Scenario: a provider is connected and the container is rebuilt

- **WHEN** a provider is connected from the web UI's Settings and the Dev
  Container is rebuilt
- **THEN** the provider is still connected and earlier sessions are listed.

#### Scenario: a second worktree starts

- **WHEN** another worktree's Dev Container starts on the same host
- **THEN** it sees none of the first worktree's provider logins or sessions.

## Rationale

### The port is always passed explicitly

OpenCode reads port 0 as "4096 if free, otherwise any port", so the server is
always started with `--port`: a taken port fails the start rather than moving
the server to a port Coder's forwarding does not expect.

Rejected:

- **Leaving the port to OpenCode's default.** The server would silently move to
  an unforwarded port.

### The Coder pane runs the server without `DISPLAY`

The Coder agent starts the server at every workspace start, with the Xpra
desktop already running, so the pane removes `DISPLAY` and a server start can
never open a browser window on that desktop.

### A missing Coder password generates a local one

OpenCode v2's server always requires a password, with basic-auth user
`opencode`, and picks its own random one when `OPENCODE_SERVER_PASSWORD` is
unset. The start generates a password file instead and binds loopback, so the
web UI stays usable in a workspace that lacks the Coder secret. The password is
never printed, because anyone who can read the agent-start log would have it.

Rejected:

- **Refusing to start without `OPENCODE_SERVER_PASSWORD`.** It takes the web UI
  away from every workspace without the secret.
- **Printing the generated password.** The agent-start log would expose it.

### The printed link is the server's root URL

OpenCode v2's web UI has no route or query parameter that opens a directory, so
the link is the server's root.

Rejected:

- **A link to a session.** The only session route needs an existing session,
  which the start would have to create on every run.

### OpenCode's data directory is never shared between instances

The data directory holds a WAL-mode SQLite database and per-project snapshot
repositories, which concurrent containers writing one copy would corrupt.

Rejected:

- **A data directory shared by every worktree.** Concurrent writers corrupt the
  database and the snapshot repositories.
