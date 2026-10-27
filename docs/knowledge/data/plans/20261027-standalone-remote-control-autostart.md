---
type: plan
created: 2026-10-27
release:
- features/standalone-remote-control-autostart
description: Opt the standalone agent-opencode runtime into Claude Remote Control with AGENTDEV_CLAUDE_RC_MODE, through a supervised remote-control watcher that waits for a claude.ai login, starts claude-remote, and restarts it within the recovery budget.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-27T12:30:00Z
sources:
- resource: docs/knowledge/data/backlog/standalone-claude-remote-control.md
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: .devcontainer/scripts/runtime-supervisor.py
- resource: .devcontainer/scripts/runtime-health.sh
- resource: docker/opencode/supervisord.conf
- resource: docker/opencode/agent-opencode.Dockerfile
- resource: docker/opencode/runtime.env.example
- resource: docker/opencode/README.md
- resource: compose.opencode.yml
---

# Start Claude Remote Control in the standalone runtime

## Context

[Remote Control autostart in the standalone
runtime](../features/standalone-remote-control-autostart.md) grows from the
backlog task [Start Claude Remote Control in the standalone runtime when
asked](../backlog/standalone-claude-remote-control.md). Only the Coder agent
starts Remote Control today; the standalone `agent-opencode` runtime has no
component for it, so a project container never starts it, even with a claude.ai
login in its auth volume. The maintainer asked for standalone support, gated on
`AGENTDEV_CLAUDE_RC_MODE`, and chose a supervised watcher as what starts Remote
Control after a login that happens once the runtime is already up.

The contracts are [Claude Remote Control](../spec/claude-remote-control.md) and
`spec/standalone-opencode-runtime`, which the [standalone OpenCode container
plan](20261017-standalone-opencode-container.md) creates.

## Approach

**Gate in the runtime.** `Settings` reads `AGENTDEV_CLAUDE_RC_MODE`. Unset or
empty leaves the `remote-control` component out of the controller's services, as
`AGENTDEV_SKIP_XPRA` does for Xpra, so neither `status` nor the state file names
it. `session` or `server` includes it. Any other value, or, in server mode, an
`AGENTDEV_CLAUDE_RC_SPAWN` other than empty, `worktree`, or `same-dir`, is a
settings error, which latches a configuration failure before the bootstrap. The
gate cannot live in `claude-remote-control-start.sh`, which reads an unset mode
as `session`.

**A supervised watcher, not a one-shot.** `remote-control` is a long-running,
optional service started after `prepare`. Its program,
`runtime-remote-control.sh run`, loops every `AGENTDEV_HEALTH_INTERVAL`:

1. It compares the signature (mtime and size) of
   `$CLAUDE_SECURESTORAGE_CONFIG_DIR/.credentials.json`, in the shared auth
   volume, with the last one it checked. Only when the signature changes, and on
   its first pass, does it run `claude auth status --json` without
   `CLAUDE_CODE_OAUTH_TOKEN`, so an idle wait costs a `stat`, not a Claude
   process.
2. With no claude.ai login, it writes `waiting for a claude.ai login` to
   `$XDG_RUNTIME_DIR/remote-control.status` and keeps waiting. A login that
   expires clears the credential file, which changes its signature, so the
   watcher returns to waiting rather than failing.
3. With a claude.ai login and no live `claude-remote` session on
   `tmux -L claude-remote`, it runs `claude-remote-control-start.sh` with an
   empty `AGENTDEV_CLAUDE_RC_SPAWN` removed from its environment, since the
   script treats a set-but-empty spawn mode as invalid. A non-zero exit ends the
   watcher with that status. Once the session is live, the status file reads
   `running in tmux session claude-remote`.
4. With a claude.ai login, a session that this watcher saw live and is now gone
   ends the watcher with a non-zero status naming `claude-remote`.

Ending the watcher hands a crashed session to the controller's existing
recovery: bounded attempts with backoff, a budget reset after a healthy period,
and, once exhausted, a degraded runtime with a `retry remote-control` command,
or a latch under strict startup. A restarted watcher adopts a live session,
because the start script reuses one. The readiness probe
`runtime-health.sh remote-control` passes once the watcher has written its
status file, so waiting for a login keeps the component `ready` and the runtime
`ready`. `runtime-health.sh status` prints the `remote-control` line from the
status file.

Rejected: a one-shot whose "no login" skip is retried by hand or on the next
container start. It needs an operator action after the first `/login`, and
nothing restarts a session that exits. Polling `claude auth status` on every
tick was rejected for the cost of a Claude process every interval.

## Implementation Steps

### Task 1: Gate the remote-control component on the mode

**Files:** Modify: `.devcontainer/scripts/runtime-supervisor.py`,
`docker/opencode/supervisord.conf`,
`scripts/tests/test_agent_runtime_supervision.py`

- [x] `Settings` parses `AGENTDEV_CLAUDE_RC_MODE` (empty, `session`, `server`)
  and, in server mode, `AGENTDEV_CLAUDE_RC_SPAWN` (empty, `worktree`,
  `same-dir`); any other value is recorded in `errors` naming the variable and
  its valid values.
  - **Evidence:** commit "Gate standalone Remote Control on
    AGENTDEV_CLAUDE_RC_MODE": `Settings.from_env` and `SettingsParser.choice`;
    `test_an_unrecognized_remote_control_setting_latches_before_the_bootstrap`
    and `test_a_session_mode_ignores_the_spawn_setting` in
    `test_agent_runtime_supervision.py`, run as root (sudo, the venv
    interpreter) with
    `-k "remote_control or real_probe or shipped_config or dependency_order"`:
    13 passed.
- [x] `SERVICES` gains `Service('remote-control', after=('prepare',))`, optional
  and long-running; `Controller` leaves it out when the mode is empty.
  - **Evidence:** commit "Gate standalone Remote Control on
    AGENTDEV_CLAUDE_RC_MODE": `test_remote_control_is_left_out_without_a_mode`
    and `test_a_remote_control_mode_starts_it_after_prepare`, run as root (sudo,
    the venv interpreter) with
    `-k "remote_control or real_probe or shipped_config or dependency_order"`:
    13 passed.
- [x] `supervisord.conf` adds `[program:remote-control]` running
  `runtime-supervisor.py exec remote-control /opt/agentdev-runtime/runtime-remote-control.sh run`
  as the runtime user, in the same shape as the other user programs.
  - **Evidence:** commit "Gate standalone Remote Control on
    AGENTDEV_CLAUDE_RC_MODE":
    `test_shipped_config_runs_user_services_unprivileged_and_logs_to_stdout`
    covers the program, run as root (sudo, the venv interpreter) with
    `-k "remote_control or real_probe or shipped_config or dependency_order"`:
    13 passed.
- [x] Supervision tests, through the existing fake-service harness: unset mode
  starts no `remote-control` and the state file has no such component; `session`
  and `server` start it after `prepare`; an unrecognized mode or server-mode
  spawn latches a configuration failure naming the variable; its failure
  degrades the runtime while OpenCode serves, and latches under strict startup.
  - **Evidence:** commit "Gate standalone Remote Control on
    AGENTDEV_CLAUDE_RC_MODE": the six `remote_control` tests in
    `test_agent_runtime_supervision.py`, including
    `test_a_failing_remote_control_degrades_while_opencode_serves` and
    `test_strict_startup_latches_on_a_failing_remote_control`, run as root
    (sudo, the venv interpreter) with
    `-k "remote_control or real_probe or shipped_config or dependency_order"`:
    13 passed.

### Task 2: Supervise the watcher

**Files:** Create: `.devcontainer/scripts/runtime-remote-control.sh`,
`scripts/tests/test_runtime_remote_control.py`; Modify:
`.devcontainer/scripts/runtime-health.sh`,
`scripts/tests/test_agent_runtime_supervision.py`

- [ ] `runtime-remote-control.sh run` implements the loop in `## Approach`, and
  `runtime-remote-control.sh check` passes only when the status file exists.
- [ ] `runtime-health.sh remote-control` runs that check as the runtime user,
  and `runtime-health.sh status` prints `  remote-control: <status file line>`
  whenever the state file names the component.
- [ ] Watcher tests with fake `claude` and `tmux`: no credential file writes the
  waiting status and runs no `claude auth status` on later ticks; a credential
  file appearing with a claude.ai login starts the session once; a setup-token
  login keeps waiting; an expired login returns to waiting; an already-live
  session is adopted without a start; a seen session that disappears ends the
  watcher non-zero; a start-script failure ends it with that status; an empty
  `AGENTDEV_CLAUDE_RC_SPAWN` does not reach the start script.
- [ ] `test_every_supervised_service_has_a_real_probe` and the shipped-config
  test cover `remote-control`.

### Task 3: Pass the settings through Compose

**Files:** Modify: `compose.opencode.yml`,
`docker/opencode/runtime.env.example`,
`scripts/tests/test_agent_runtime_compose.py`

- [ ] `compose.opencode.yml` passes `AGENTDEV_CLAUDE_RC_MODE` and
  `AGENTDEV_CLAUDE_RC_SPAWN` as `${VAR:-}`, and `runtime.env.example` documents
  both, empty by default, with their valid values.
- [ ] A Compose test asserts both reach the container, and
  `test_env_example_documents_every_interpolated_setting` passes.

### Task 4: Accept the watcher in a container

**Files:** Modify: `scripts/tests/test_agent_runtime_acceptance.py`

- [ ] Container acceptance, with a fake `claude` placed ahead of the real one on
  the runtime user's `PATH` (acceptance has no claude.ai login): with the mode
  unset, no `claude-remote` tmux session exists and `status` names no
  `remote-control`; with `server` and no login, the runtime is `ready` and
  `status` says it is waiting for a claude.ai login; after the fake login
  appears, `claude-remote` runs in `/workspaces/project` with no terminal
  interaction; after the session is killed, it comes back.

### Task 5: Document the runtime's Remote Control

**Files:** Modify: `docker/opencode/README.md`,
`docs/knowledge/data/architecture/standalone-opencode-runtime.md`

- [ ] The README's settings and log-in steps say how to opt in, that Remote
  Control starts by itself after `claude`'s `/login`, and how to read its line
  in `status`.
- [ ] The architecture doc records the watcher: the gate in the runtime, the
  credential-signature trigger, recovery through the controller's budget, and
  the rejected one-shot and per-tick polling.

### Task 6: Confirm Remote Control on a real deployment

**Files:** none

- [ ] On a standalone deployment with `AGENTDEV_CLAUDE_RC_MODE=server` and no
  Claude login, `status` says it is waiting; after `/login` from
  `docker exec -u agent -it <container> claude`, `claude-remote` starts without
  a restart, and a conversation started from claude.ai/code in that environment
  works in the workspace.

## Spec changes

[Claude Remote Control](../spec/claude-remote-control.md): its first requirement
names the standalone watcher as the second thing that runs the start script, and
a new requirement covers the standalone runtime. Ship also replaces the setup
procedure's "Autostart is Coder-only" with the standalone opt-in.

``` markdown
## MODIFIED Requirements

### Requirement: Remote Control autostarts only on a live claude.ai login

`claude-remote-control-start.sh` SHALL start Remote Control in exactly one
detached tmux session named `claude-remote`, on the dedicated tmux server
`tmux -L claude-remote`, naming the Remote Control session after
`CODER_WORKSPACE_NAME` when it is set, only when `claude auth status --json`
reports `loggedIn: true` with `authMethod: "claude.ai"`. The Coder template's
`coder_script` on the dev container's sub-agent runs it on every agent start,
and the standalone runtime's `remote-control` watcher runs it when
`AGENTDEV_CLAUDE_RC_MODE` is set; no devcontainer lifecycle hook runs it.
Repeated or concurrent runs SHALL reuse a live session rather than create
another. It SHALL skip startup when `claude` or `tmux` is unavailable. The
Claude process SHALL NOT receive `CLAUDE_CODE_OAUTH_TOKEN`.

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

## ADDED Requirements

### Requirement: the standalone runtime starts Remote Control when a mode is set

A nonempty `AGENTDEV_CLAUDE_RC_MODE` SHALL add an optional, supervised
`remote-control` component to the standalone runtime, started after `prepare`;
unset or empty SHALL leave the component out, so the runtime neither starts nor
reports it. A value other than `session` or `server`, or in server mode an
`AGENTDEV_CLAUDE_RC_SPAWN` other than empty, `worktree`, or `same-dir`, SHALL
latch a configuration failure naming the variable before the bootstrap. While no
claude.ai login exists, the component SHALL be ready, the runtime SHALL stay
`ready`, and `runtime-health.sh status` SHALL say it is waiting for a claude.ai
login. Once a claude.ai login exists, the component SHALL run
`claude-remote-control-start.sh` as the runtime user in the workspace folder,
with no operator action, and check for the login without starting a Claude
process unless the credential file changed. When a `claude-remote` session it
saw live is gone while the login holds, it SHALL restart the session within the
runtime's recovery budget for optional services.

#### Scenario: the mode is unset

- **WHEN** the standalone runtime starts with `AGENTDEV_CLAUDE_RC_MODE` unset or
  empty
- **THEN** no `claude-remote` tmux session exists and `status` names no
  `remote-control` component.

#### Scenario: the mode is set before any login

- **WHEN** the runtime starts with `AGENTDEV_CLAUDE_RC_MODE=server` and no
  claude.ai login in the auth volume
- **THEN** the runtime reports `ready` and `status` says Remote Control is
  waiting for a claude.ai login.

#### Scenario: the operator logs in after the runtime started

- **WHEN** `/login` completes in a container sharing the auth volume while the
  watcher waits
- **THEN** `claude-remote` starts in the workspace folder without a container
  restart, and a conversation started from claude.ai/code works there.

#### Scenario: the Remote Control session exits

- **WHEN** the live `claude-remote` session ends while the login holds
- **THEN** the runtime restarts it, and once the recovery budget is exhausted
  reports degraded naming `remote-control`, or latches failed under strict
  startup.

#### Scenario: the mode value is unrecognized in the runtime

- **WHEN** the runtime starts with `AGENTDEV_CLAUDE_RC_MODE=sever`
- **THEN** it latches a configuration failure naming `AGENTDEV_CLAUDE_RC_MODE`
  before the bootstrap.
```

`spec/standalone-opencode-runtime`: the image no longer promises never to
autostart Claude Code, and Remote Control joins the optional services.

``` markdown
## MODIFIED Requirements

### Requirement: a dedicated image owns a single-project runtime

`ghcr.io/plume-works/agent-opencode` SHALL derive from the corresponding digest
of `agent-desktop`, provide linux/amd64 and linux/arm64 images, and start its
environment without Coder, a Dev Containers client, or project scaffolding.
It SHALL keep Claude Code and Codex available without autostarting them, except
Claude Remote Control when `AGENTDEV_CLAUDE_RC_MODE` opts in, and SHALL omit
Docker MCP gateway integration.

#### Scenario: an ordinary checkout is mounted

- **WHEN** an operator starts the dedicated image with valid required configuration
- **THEN** it prepares that single project and starts OpenCode and its required services using image-owned shared helpers.

#### Scenario: the existing image is used

- **WHEN** an existing consumer starts agent-desktop or runs its devcontainer hooks
- **THEN** its command defaults, Coder integration, opt-outs, and lifecycle failure semantics remain compatible.

### Requirement: services have supervised bounded recovery

The runtime SHALL supervise OpenCode, DinD, CBM, D-Bus/keyring, enabled Xpra,
and enabled Remote Control with readiness probes, bounded startup, bounded
per-service retries/backoff, and orderly termination. It SHALL detect actual
daemon failure even when the public tool daemonizes, mark dependency outages
unready, and recover affected clients coherently. OpenCode and D-Bus/keyring
SHALL be core services; DinD, CBM, Xpra, and Remote Control SHALL be optional,
and OpenCode SHALL NOT wait for Xpra. A core service exhausting its budget SHALL
latch the runtime failed; an optional one SHALL mark it degraded while OpenCode
keeps serving. With `AGENTDEV_STRICT_STARTUP=true`, every optional failure SHALL
be treated as a core failure. PID 1 SHALL keep running in both states and SHALL
exit nonzero only when its controller or supervisord fails. Xpra SHALL start by
default with an explicit disable option.

#### Scenario: a running service fails

- **WHEN** a supervised process exits or fails readiness
- **THEN** the runtime becomes unready and restarts that service within its recovery budget without duplicating daemons or rerunning project mutation unnecessarily.

#### Scenario: a core service keeps failing

- **WHEN** OpenCode or D-Bus/keyring exhausts its bounded recovery budget
- **THEN** the runtime latches failed, records the cause, and keeps PID 1 running without restarting the container.

#### Scenario: an optional service keeps failing

- **WHEN** DinD, CBM, Xpra, or Remote Control exhausts its bounded recovery budget without strict startup
- **THEN** OpenCode keeps serving and the runtime reports degraded, naming that service.

#### Scenario: strict startup is selected

- **WHEN** `AGENTDEV_STRICT_STARTUP=true` and any optional service or preparation step fails
- **THEN** the runtime latches failed and OpenCode is not served.

#### Scenario: the controller fails

- **WHEN** the supervisor's controller or supervisord itself terminates unexpectedly
- **THEN** PID 1 exits nonzero, and the container's restart policy applies.

#### Scenario: the container is stopped

- **WHEN** PID 1 receives SIGTERM
- **THEN** it stops managed clients and services in dependency order, bounds shutdown, and reaps remaining processes.
```

## Depends on

[Ship a standalone OpenCode
container](20261017-standalone-opencode-container.md) — it creates
`spec/standalone-opencode-runtime`, which this plan modifies.

## Verification

- `uv run pytest scripts/tests/test_runtime_remote_control.py scripts/tests/test_agent_runtime_supervision.py scripts/tests/test_agent_runtime_compose.py scripts/tests/test_claude_remote_control_start.py`
- `.devcontainer/scripts/test-agent-runtime.sh` against a locally built
  `agent-opencode`, including the Task 4 acceptance test.
- `shellcheck .devcontainer/scripts/runtime-remote-control.sh .devcontainer/scripts/runtime-health.sh`
  and `python-lint-check.sh`.
- Task 6 on a real deployment with a claude.ai login.

## Out of scope

- Coder and Dev Containers starts: `coder-agent-start.sh` and the lifecycle
  hooks are unchanged.
- A Remote Control session name in the standalone runtime: with no
  `CODER_WORKSPACE_NAME`, Claude's default name applies.
- Restarting a session that exits while no claude.ai login exists; the watcher
  only waits then.
- Changes to `claude-remote-control-start.sh` or the session and server-mode
  behavior it runs.

## Key references

Verified anchor points (line numbers as of 2026-10-27):

- `.devcontainer/scripts/runtime-supervisor.py:118` — `Settings`
- `.devcontainer/scripts/runtime-supervisor.py:138` — `Settings.from_env`
- `.devcontainer/scripts/runtime-supervisor.py:229` — `Service`
- `.devcontainer/scripts/runtime-supervisor.py:246` — `SERVICES`
- `.devcontainer/scripts/runtime-supervisor.py:289` — `Controller.__init__`
  service filter
- `.devcontainer/scripts/runtime-supervisor.py:805` — `preflight`
- `.devcontainer/scripts/runtime-health.sh:28` — runtime-user probe list
- `.devcontainer/scripts/runtime-health.sh:58` — `status`
- `.devcontainer/scripts/claude-remote-control-start.sh:4` — mode default
- `.devcontainer/scripts/claude-remote-control-start.sh:62` — live-session reuse
- `docker/opencode/supervisord.conf:195` — `[program:opencode]`
- `docker/opencode/agent-opencode.Dockerfile:37` —
  `CLAUDE_SECURESTORAGE_CONFIG_DIR`
- `docker/opencode/agent-opencode.Dockerfile:42` — `XDG_RUNTIME_DIR`
- `compose.opencode.yml:30` — `AGENTDEV_STRICT_STARTUP`
- `docker/opencode/runtime.env.example:53` — `AGENTDEV_STRICT_STARTUP`
- `docker/opencode/README.md:146` — `## 6. Log in`
- `scripts/tests/test_agent_runtime_supervision.py:97` — `build_config`
- `scripts/tests/test_agent_runtime_supervision.py:685` —
  `test_every_supervised_service_has_a_real_probe`
- `scripts/tests/test_agent_runtime_compose.py:137` —
  `test_env_example_documents_every_interpolated_setting`
- `scripts/tests/test_agent_runtime_acceptance.py:261` — `make_runtime`
