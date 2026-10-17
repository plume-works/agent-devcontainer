---
type: plan
created: 2026-10-16
release:
- features/opencode-web-coder-autostart
description: Start the OpenCode web UI from the Coder agent-start script, bound to localhost unless a server password is set, with OpenCode logins on the shared auth volume and its data directory on a per-worktree volume.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-16T18:30:00Z
sources:
- resource: .devcontainer/scripts/coder-agent-start.sh
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: .devcontainer/scripts/link-codex-auth.sh
- resource: .devcontainer/devcontainer.json
- resource: https://github.com/sst/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/auth/index.ts
- resource: https://github.com/sst/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/cli/cmd/web.ts
- resource: https://github.com/sst/opencode/blob/733b2c627e5aec39cb33cc22373bdce33053ef2c/packages/opencode/src/server/server.ts
---

# Autostart the OpenCode web UI on Coder

## Context

[OpenCode web UI autostart on
Coder](../features/opencode-web-coder-autostart.md) is the feature this plan
builds. OpenCode is installed in the image, but nothing starts its server, and
its data directory, `~/.local/share/opencode`, is on no volume, so a Dev
Container rebuild loses provider logins and session chats.

[Agent auth persistence](../architecture/agent-auth-persistence.md) is the split
this plan extends to OpenCode: credentials on the shared `agentdev-agents-auth`
volume, path-bearing state on a per-instance volume. [Coder IDE baseline
template](../spec/coder-ide-baseline.md) makes `coder-agent-start.sh` the only
start hook and the only place Coder user secrets reach.

OpenCode v1.19.0 behavior this plan relies on:

- `auth.json` is rewritten in place (`fs.writeFile`, then `chmod 0600`) by every
  writer — CLI and web UI login and logout, OAuth callbacks, plugin token
  refresh — so a symlink at its path survives. Writes take no lock.
- `opencode web` serves the API and the web UI from one process. With no
  `OPENCODE_SERVER_PASSWORD` it serves unauthenticated and warns. It tries to
  open the UI in a browser and ignores a failure.
- Port 0 means "4096 if free, otherwise any port".

## Approach

Four pieces, each following an existing pattern:

- **Login symlink.** `link-opencode-auth.sh` mirrors `link-codex-auth.sh`: it
  moves a regular `~/.local/share/opencode/auth.json` into
  `/root/.agents-auth/opencode/` and symlinks it back. It does not create the
  target; OpenCode's first login writes through the dangling link.
  `postCreateCommand.sh` and `postStartCommand.sh` run it, as they run the Codex
  one.
- **Per-worktree data volume.** `devcontainer.json` mounts a Compose-prefixed
  `agentdev-opencode` volume at `/root/.local/share/opencode`.
- **Server start.** `opencode-web-start.sh` mirrors the tmux handling of
  `claude-remote-control-start.sh`, minus its login gate: a detached session
  `opencode` on `tmux -L opencode` in the workspace folder, reused when live.
  The pane runs `opencode web --port 4096` with `--hostname 0.0.0.0` when
  `OPENCODE_SERVER_PASSWORD` is non-empty and `--hostname 127.0.0.1` otherwise.
  It skips when `opencode` or `tmux` is missing.
- **Coder wiring.** `coder-agent-start.sh` runs it after the credential helper
  and before the final `exec`; a failure warns and Remote Control still starts.

Assumptions:

- The pane runs with `DISPLAY` removed, so `opencode web` cannot open a browser
  window on the Xpra desktop at every workspace start.
- The port is passed explicitly, so a taken port fails the start rather than
  moving the server to a port Coder's forwarding does not expect.

Rejected:

- **Sharing the whole data directory across worktrees.** It holds a WAL-mode
  SQLite database and per-project snapshot repositories; concurrent containers
  writing one copy risk corruption.
- **Moving the data directory with `XDG_DATA_HOME`.** It moves every XDG-aware
  tool's data, not just OpenCode's, and still leaves logins unshared.
- **Starting from `postStartCommand.sh`.** It runs before the Coder agent
  exists, so the server would miss Coder user secrets, including
  `OPENCODE_SERVER_PASSWORD`.

## Implementation Steps

### Task 1: Share the OpenCode login through the auth volume

**Files:** Create: `.devcontainer/scripts/link-opencode-auth.sh`,
`scripts/tests/test_link_opencode_auth.py`; Modify:
`.devcontainer/scripts/postCreateCommand.sh`,
`.devcontainer/scripts/postStartCommand.sh`

- [x] Tests first, with the auth directory and data directory overridable by
  environment so no test touches `/root`:
  - no local file: the local path becomes a symlink to the shared target; the
    target is not created;
  - a regular local file: its content moves to the shared target, mode `0600`,
    and the local path becomes the symlink;
  - an existing symlink: a rerun leaves it pointing at the shared target and the
    target's content unchanged;
  - the shared directory ends at mode `0700`.
  - **Evidence:** commit "feat(devcontainer): share the OpenCode login through
    the auth volume": `scripts/tests/test_link_opencode_auth.py`, one test per
    case, overriding `HOME` and `AGENTDEV_AGENTS_AUTH_DIR`; all four fail before
    the script exists.
- [x] Script, shellcheck clean; the tests pass.
  - **Evidence:** commit "feat(devcontainer): share the OpenCode login through
    the auth volume": `link-opencode-auth.sh`; `shellcheck` clean;
    `uv run pytest scripts/tests/test_link_opencode_auth.py` 4 passed.
- [x] `postCreateCommand.sh` creates `/root/.agents-auth/opencode` beside the
  Claude and Codex directories and runs the script after `link-codex-auth.sh`;
  `postStartCommand.sh` runs it after `link-codex-auth.sh`.
  - **Evidence:** commit "feat(devcontainer): share the OpenCode login through
    the auth volume": both hooks call `link-opencode-auth.sh` right after
    `link-codex-auth.sh`; `shellcheck` clean on both.

### Task 2: Keep OpenCode's data directory on a per-worktree volume

**Files:** Modify: `.devcontainer/devcontainer.json`

- [x] Add a `mounts` entry `agentdev-opencode` → `/root/.local/share/opencode`,
  `type: volume`, after `agentdev-codex`, with a comment pointing at
  `architecture/agent-auth-persistence` and `link-opencode-auth.sh`.
  - **Evidence:** commit "feat(devcontainer): keep OpenCode's data directory on
    a per-worktree volume": the `agentdev-opencode` mount follows
    `agentdev-codex`;
    `bunx --bun json5 --validate .devcontainer/devcontainer.json` passes.

### Task 3: Start `opencode web` in a reusable tmux session

**Files:** Create: `.devcontainer/scripts/opencode-web-start.sh`,
`scripts/tests/test_opencode_web_start.py`

- [x] Tests first, against a fake `tmux` and a fake `opencode` in the manner of
  `test_claude_remote_control_start.py`:
  - no password: the pane command runs
    `opencode web --port 4096 --hostname 127.0.0.1` in the workspace folder,
    without `DISPLAY`;
  - `OPENCODE_SERVER_PASSWORD` set: `--hostname 0.0.0.0`, and the password
    reaches the pane's environment;
  - `OPENCODE_SERVER_PASSWORD` set but empty: `127.0.0.1`;
  - a live `opencode` session on `tmux -L opencode`: no new session, exit 0;
  - `opencode` or `tmux` missing: exit 0 with a skip message.
  - **Evidence:** commit "feat(devcontainer): start the OpenCode web UI in a
    reusable tmux session": `scripts/tests/test_opencode_web_start.py`; the
    fake-tmux cases cover the bind, reuse, and skip cases, and a real-tmux case
    shows the password reaching the pane without `DISPLAY`; all seven fail
    before the script exists.
- [x] Script, shellcheck clean; the tests pass.
  - **Evidence:** commit "feat(devcontainer): start the OpenCode web UI in a
    reusable tmux session": `opencode-web-start.sh`; `shellcheck` clean;
    `uv run pytest scripts/tests/test_opencode_web_start.py` 7 passed, the
    real-tmux case run.

### Task 4: Run the start script from the Coder agent start

**Files:** Modify: `.devcontainer/scripts/coder-agent-start.sh`,
`scripts/tests/test_coder_agent_start.py`

- [x] Tests: the call order is prune, credential helper,
  `opencode-web-start.sh`, Remote Control; a failing `opencode-web-start.sh`
  warns on stderr and Remote Control still starts; the OpenCode start sees the
  caller's environment.
  - **Evidence:** commit "feat(devcontainer): start the OpenCode web UI from the
    Coder agent start": `test_coder_agent_start.py` gains the
    `opencode-web-start.sh` fake, the call-order assertion, and two new tests;
    four fail against the previous script.
- [x] Script change; `uv run pytest scripts/tests/test_coder_agent_start.py`
  passes.
  - **Evidence:** commit "feat(devcontainer): start the OpenCode web UI from the
    Coder agent start": `coder-agent-start.sh` runs `opencode-web-start.sh`
    after the credential helper with a warn-and-continue guard; `shellcheck`
    clean; 6 passed.

### Task 5: Record OpenCode in the auth-persistence architecture

**Files:** Modify: `docs/knowledge/data/architecture/agent-auth-persistence.md`

- [ ] The Decision section names OpenCode's shared `auth.json` symlink and its
  `agentdev-opencode` volume beside Claude and Codex, and Consequences records
  that concurrent OpenCode login writes are last-writer-wins.

### Task 6: Refresh the codebase map

**Files:** Modify: `docs/knowledge/data/codebase/devcontainer/scripts.md`, and
any other `data/codebase/` doc `stale-map-docs.py` reports

- [ ] Run `/agentdev:iwe-map` in refresh mode over the docs covering the changed
  scripts and `devcontainer.json`, adding rows for the two new scripts.

### Task 7: Verify in a live Coder workspace

- [ ] On a Coder workspace whose checkout carries this change, after a rebuild:
  `tmux -L opencode capture-pane -p -t opencode` shows the web interface on port
  4096; the UI opens through Coder port forwarding; a provider connected from
  Settings appears in `/root/.agents-auth/opencode/auth.json` with
  `~/.local/share/opencode/auth.json` still a symlink; after a second rebuild
  the provider is still connected and the earlier session is listed.

### Task 8: Verify the password-protected bind

- [ ] With `OPENCODE_SERVER_PASSWORD` set as a Coder user secret and the
  workspace restarted, the server listens on `0.0.0.0:4096` and an
  unauthenticated request gets `401`.

## Spec changes

A new spec, `spec/opencode-web`, holds the server contract; it exposes a network
service, so the full requirements are stated. [Catalog
lifecycle](../spec/catalog-lifecycle.md) widens its credential-sharing
requirement to OpenCode.

``` markdown
## ADDED Requirements

### Requirement: the Coder agent start runs the OpenCode web UI

`coder-agent-start.sh` SHALL run `opencode-web-start.sh` on every agent start,
before Remote Control starts. The script SHALL start `opencode web` in exactly
one detached tmux session named `opencode` on the dedicated tmux server
`tmux -L opencode`, in the workspace folder, without checking for a provider
login. Repeated runs SHALL reuse a live session. It SHALL skip startup when
`opencode` or `tmux` is unavailable. A failure SHALL NOT stop Remote Control
from starting.

#### Scenario: a workspace starts

- **WHEN** the Coder agent starts and no `opencode` session is live
- **THEN** `opencode web` runs in the `opencode` session on `tmux -L opencode`.

#### Scenario: the agent start runs again

- **WHEN** the `opencode` session is already live
- **THEN** no second session or server starts.

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

## MODIFIED Requirements

### Requirement: only agent credentials are shared across worktrees

The `agentdev-agents-auth` volume SHALL hold only each agent's authentication
state (mounted at `/root/.agents-auth/<agent>`); all other plugin/install state
lives in the per-devcontainer-instance `agentdev-claude` / `agentdev-codex` /
`agentdev-opencode` volumes.

#### Scenario: two worktrees of the same repository are opened as separate devcontainers

- **WHEN** both attach
- **THEN** each gets its own catalog install (scoped per instance) but shares
  the same logged-in Claude/Codex/OpenCode credentials (scoped to the shared
  auth volume).
```

## Verification

- `uv run pytest scripts/tests/test_link_opencode_auth.py scripts/tests/test_opencode_web_start.py scripts/tests/test_coder_agent_start.py`
  passes.
- `shellcheck` is clean on the new and changed scripts.
- Tasks 7 and 8 pass on a live Coder workspace.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- **Picking up catalog changes in a running server.** Coder-started servers keep
  the catalog they read at start until restart; the feature records this as a
  risk.
- **Locking concurrent `auth.json` writes.** OpenCode takes no lock; this plan
  accepts last-writer-wins.
- **Autostart outside Coder.** Local Dev Containers and CI do not start the
  server.
- **Firewall entries for OpenCode.** The firewall stays opt-in and untouched.

## Key references

Verified anchor points (line numbers as of 2026-10-16):

- `.devcontainer/scripts/coder-agent-start.sh:9-17` — prune, credential helper,
  `exec` of Remote Control
- `.devcontainer/scripts/claude-remote-control-start.sh:29` — `session`; `:37` —
  live-session check; `:43` — `tmux_start`
- `.devcontainer/scripts/link-codex-auth.sh:19-31` — move-then-symlink of a
  shared `auth.json`
- `.devcontainer/scripts/postCreateCommand.sh:72-73` — shared auth
  subdirectories; `:79` — `link-codex-auth.sh`
- `.devcontainer/scripts/postStartCommand.sh:27` — `link-codex-auth.sh`
- `.devcontainer/devcontainer.json:60` — `mounts`; `:97-99` — `agentdev-codex`
  mount
- `scripts/tests/test_coder_agent_start.py:13` — `run_agent_start`; `:43` —
  call-order test
- `scripts/tests/test_claude_remote_control_start.py:33` — `run_with_fake_tmux`
- `docs/knowledge/data/spec/catalog-lifecycle.md:122` — credential-sharing
  requirement
