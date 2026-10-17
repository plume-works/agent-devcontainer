---
type: feature
stage: implemented
description: On Coder workspaces, the agent-start script runs the OpenCode web UI in the background, reachable from a dashboard app and a printed link into the workspace folder, with provider logins shared across worktrees and session chats kept per worktree across rebuilds.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-17T12:00:00Z
sources:
- resource: .devcontainer/scripts/coder-agent-start.sh
- resource: .devcontainer/scripts/link-codex-auth.sh
- resource: .devcontainer/devcontainer.json
- resource: https://github.com/plume-works/coder-ide-baseline
- resource: https://github.com/sst/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/auth/index.ts
- resource: https://github.com/sst/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/cli/cmd/web.ts
---

# OpenCode web UI autostart on Coder

## Purpose

OpenCode's web UI is only available after someone starts `opencode web` by hand,
and its provider logins and session chats live in the container's data
directory, so a Dev Container rebuild loses both.

## Behaviour

**Coder starts it.** `coder-agent-start.sh` starts `opencode web` in a detached
tmux session on its own tmux server, `tmux -L opencode`, on every agent start. A
live session is reused, not duplicated. There are no login prechecks: providers
are connected from the web UI's Settings.

**Local by default, exposed only behind a password.** The server listens on port
4096, OpenCode's default. It binds `127.0.0.1`, reached through Coder port
forwarding, unless `OPENCODE_SERVER_PASSWORD` is set — for example as a Coder
user secret — in which case it binds `0.0.0.0` and OpenCode requires the
password.

**One click into the workspace.** The start prints a link that opens a session
in the workspace folder, and the Coder dashboard shows an `OpenCode` app that
opens the web UI.

**Logins are shared.** `~/.local/share/opencode/auth.json` is a symlink to
`/root/.agents-auth/opencode/auth.json` on the shared `agentdev-agents-auth`
volume, so one login serves every worktree and survives a rebuild. OpenCode
writes `auth.json` in place, so login, logout, and token refresh keep the
symlink.

**Chats are per worktree.** A Compose-prefixed `agentdev-opencode` volume
mounted at `/root/.local/share/opencode` keeps the session database and the rest
of OpenCode's data directory across rebuilds.

## Edge cases

- **The catalog changes after the server started.** `postAttachCommand.sh`
  re-registers the agentdev catalog for every harness; a running server keeps
  the configuration it started with until it restarts.
- **Two worktrees write a login at the same moment.** OpenCode takes no lock on
  `auth.json`, so the last writer wins.
- **Local Dev Containers and CI.** Nothing starts the server; the volumes and
  the login symlink still apply.
- **The project sidebar starts empty.** The web UI keeps its project list in the
  browser, so the workspace folder appears there only after one "Add project"
  per browser; the printed link opens it directly regardless.
- **A repository without OpenCode.** The template gives every workspace the
  `OpenCode` app; where no server runs, it shows unhealthy.
- **No provider is logged in.** The server starts anyway; the web UI's Settings
  connects one.

## Open questions

None open.
