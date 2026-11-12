---
type: spec
description: Claude Remote Control autostarts from the Coder agent, or from the standalone runtime's supervised watcher when AGENTDEV_CLAUDE_RC_MODE opts in, only on a live claude.ai login, inheriting the agent's environment and either resuming its pinned conversation or, opted in with AGENTDEV_CLAUDE_RC_MODE=server, running a spawn-on-demand server that gives each spawned conversation its own git worktree unless AGENTDEV_CLAUDE_RC_SPAWN=same-dir, every container pre-approves Claude's first-run state unless it opts out, and the dev container's hostname, which names the Remote Control environment, says where the container came from.
sources:
- resource: .claude/.gitignore
- resource: .claude/settings.json
- resource: .devcontainer/devcontainer-init.sh
- resource: .devcontainer/docker-compose.yml
- resource: py_packages/agentdev_runtime/agentdev_runtime/remote_control.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/coder.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/claude_state.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/supervisor.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: .github/actions/run-claude-responder/action.yml
- resource: scripts/tests/test_claude_remote_control_pin.py
- resource: scripts/tests/test_claude_remote_control_session.py
- resource: scripts/tests/test_claude_remote_control_start.py
- resource: scripts/tests/test_container_hostname.py
- resource: scripts/tests/test_preapprove_claude_workspace.py
- resource: https://code.claude.com/docs/en/errors#login-expired
- resource: https://code.claude.com/docs/en/authentication
- resource: https://code.claude.com/docs/en/remote-control
- resource: https://code.claude.com/docs/en/hooks
- resource: https://code.claude.com/docs/en/worktrees
- resource: https://github.com/anthropics/claude-code/issues/21765
- resource: https://github.com/anthropics/claude-code/issues/88583
- resource: https://github.com/plume-works/coder-ide-baseline/blob/ab1c595/template/main.tf
- resource: https://coder.com/docs/v2.37/user-guides/user-secrets
---

# Claude Remote Control

Claude credentials come only from a `/login` inside a container, persisted in
the shared `agentdev-agents-auth` volume ([Devcontainer
state](devcontainer-state.md)). On top of that login, a Coder workspace starts
Claude Remote Control unattended under the Coder agent, the standalone
`agentdev-deploy` runtime starts it when `AGENTDEV_CLAUDE_RC_MODE` opts in, and
every devcontainer answers Claude's first-run prompts ahead of time.

## Requirements

### Requirement: Remote Control autostarts only on a live claude.ai login

`agentdev-runtime remote-control start` SHALL start Remote Control in exactly
one detached tmux session named `claude-remote`, on the dedicated tmux server
`tmux -L claude-remote`, naming the Remote Control session after
`CODER_WORKSPACE_NAME` when it is set, only when `claude auth status --json`
reports `loggedIn: true` with `authMethod: "claude.ai"`. On Coder,
`agentdev-runtime coder start`, which the template's `coder_script` on the dev
container's sub-agent runs on every agent start, runs it after its other steps,
and nothing restarts a session that ends until the next agent start or a manual
run; the standalone runtime's `remote-control` watcher runs it when
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
other Claude process SHALL write the stored ID. The pin hook SHALL replace the
stored ID through a temporary file in the same directory and a rename, so an
interrupted write never leaves a truncated ID, and SHALL exit 0 in every case:
input that does not parse or carries no `session_id` leaves the stored ID
unchanged and writes a message to stderr. A transient failure to reconnect a
resumed conversation leaves Claude running with Remote Control off; running
`/remote-control` in the session restores it.

#### Scenario: the Coder agent restarts

- **WHEN** the `coder_script` runs while `claude-remote` is already live
- **THEN** it leaves the existing session running and creates no additional
  Claude process.

#### Scenario: the saved login has expired

- **WHEN** the credential file exists but `claude auth status --json` reports
  `loggedIn: false`
- **THEN** no session is started and the command exits successfully.

#### Scenario: only a setup token is available

- **WHEN** `claude auth status --json` reports `loggedIn: true` with an
  `authMethod` other than `claude.ai`
- **THEN** no session is started.

#### Scenario: the operator logs in after the workspace started

- **WHEN** an operator completes `/login` and runs the command from a Coder
  terminal
- **THEN** `claude-remote` starts without a workspace restart.

#### Scenario: the Remote Control session ends on Coder

- **WHEN** the `claude-remote` session exits in a Coder workspace, a server-mode
  server included
- **THEN** Remote Control stays off until the next agent start, or until an
  operator runs the command from a Coder terminal.

#### Scenario: the session starts in a Coder workspace

- **WHEN** the command starts `claude-remote` with `CODER_WORKSPACE_NAME` set
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

#### Scenario: the pin hook receives unusable input

- **WHEN** the pin hook's input is not JSON or has no `session_id`
- **THEN** the stored ID is unchanged, a message goes to stderr, and the hook
  exits 0, so the session continues.

### Requirement: the standalone runtime starts Remote Control when a mode is set

A nonempty `AGENTDEV_CLAUDE_RC_MODE` SHALL add an optional, supervised
`remote-control` component to the standalone runtime, started after `prepare`;
unset or empty SHALL leave the component out, so the runtime neither starts nor
reports it. A value other than `session` or `server`, or in server mode an
`AGENTDEV_CLAUDE_RC_SPAWN` other than empty, `worktree`, or `same-dir`, SHALL
latch a configuration failure naming the variable before the bootstrap. While no
claude.ai login exists, the component SHALL be ready, the runtime SHALL stay
`ready`, and `agentdev-runtime health status` SHALL say it is waiting for a
claude.ai login. Once a claude.ai login exists, the component SHALL run
`agentdev-runtime remote-control start` as the runtime user in the workspace
folder, with no operator action, and check for the login without starting a
Claude process unless the credential file changed. When a `claude-remote`
session it saw live is gone while the login holds, it SHALL restart the session
within the runtime's recovery budget for optional services. A start that returns
without leaving a live `claude-remote` session SHALL count as the session
exiting, so the runtime restarts it and, once the recovery budget is exhausted,
reports degraded naming `remote-control`, or latches failed under strict
startup.

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

### Requirement: Claude sessions default to auto mode

`.claude/settings.json` SHALL set `permissions.defaultMode` to `auto`, so a
Claude session in the workspace, the session-mode pane included, starts in
Claude Code's `auto` permission mode unless its launch names another mode.

#### Scenario: the session-mode pane starts

- **WHEN** session mode starts the pinned pane in the workspace folder
- **THEN** its conversation starts in the `auto` permission mode.

### Requirement: server mode is opt-in

`AGENTDEV_CLAUDE_RC_MODE` SHALL select the mode: `server` selects server mode,
and an unset or `session` value selects session mode. Any other value SHALL make
the command print the value and the valid options to stderr, start no session,
and exit non-zero, before any other check. In server mode,
`AGENTDEV_CLAUDE_RC_SPAWN` SHALL select the spawn mode: an unset or `worktree`
value selects `worktree`, and `same-dir` selects `same-dir`. Any other value
SHALL make the command print the value and the valid options to stderr, start no
session, and exit non-zero, before any check other than the mode's. In session
mode the command SHALL NOT read `AGENTDEV_CLAUDE_RC_SPAWN`. In server mode the
`claude-remote` session SHALL run
`claude remote-control --spawn <spawn mode> --permission-mode auto`, passing
`--name` and `--remote-control-session-name-prefix` set to
`CODER_WORKSPACE_NAME` when it is set, and SHALL neither read nor write the
stored conversation ID. `.claude/worktrees/` SHALL be ignored by git.

#### Scenario: server mode is selected

- **WHEN** the command starts `claude-remote` with
  `AGENTDEV_CLAUDE_RC_MODE=server` and `AGENTDEV_CLAUDE_RC_SPAWN` unset
- **THEN** the session runs
  `claude remote-control --spawn worktree --permission-mode auto` and reaches a
  connected server with no terminal interaction.

#### Scenario: same-dir spawn mode is selected

- **WHEN** the command starts `claude-remote` with
  `AGENTDEV_CLAUDE_RC_MODE=server` and `AGENTDEV_CLAUDE_RC_SPAWN=same-dir`
- **THEN** the session runs
  `claude remote-control --spawn same-dir --permission-mode auto`.

#### Scenario: a conversation is spawned in worktree mode

- **WHEN** a new conversation is started in the workspace's environment from
  claude.ai/code or the Claude mobile app while the server runs in worktree mode
- **THEN** it runs in its own git worktree under the workspace folder's
  `.claude/worktrees/` with the environment of the process that ran the command,
  and `git status` in the workspace folder lists none of its files.

#### Scenario: a spawned conversation starts in auto mode

- **WHEN** a conversation is spawned while the server runs in either spawn mode
- **THEN** it starts in Claude Code's `auto` permission mode.

#### Scenario: the server pre-creates its session in worktree mode

- **WHEN** `claude remote-control --spawn worktree` starts and creates its first
  session
- **THEN** that session runs in the workspace folder, not in a worktree; only
  conversations spawned after it get worktrees under `.claude/worktrees/`.

#### Scenario: a conversation is spawned in same-dir mode

- **WHEN** a new conversation is started in the workspace's environment from
  claude.ai/code or the Claude mobile app while the server runs in same-dir mode
- **THEN** it runs in the workspace folder with the environment of the process
  that ran the command.

#### Scenario: the mode value is unrecognized

- **WHEN** the command runs with `AGENTDEV_CLAUDE_RC_MODE` set to a value other
  than `server` or `session`
- **THEN** it prints the value and the valid options `server` and `session`,
  starts no session, and exits non-zero.

#### Scenario: the spawn value is unrecognized in server mode

- **WHEN** the command runs with `AGENTDEV_CLAUDE_RC_MODE=server` and
  `AGENTDEV_CLAUDE_RC_SPAWN` set to a value other than `worktree` or `same-dir`
- **THEN** it prints the value and the valid options `worktree` and `same-dir`,
  starts no session, and exits non-zero.

#### Scenario: the spawn value is set in session mode

- **WHEN** the command runs in session mode with `AGENTDEV_CLAUDE_RC_SPAWN` set
  to any value
- **THEN** it starts the pinned pane exactly as with the variable unset.

#### Scenario: the mode or spawn mode changes while a session is live

- **WHEN** the command runs with a different mode or spawn mode while
  `claude-remote` is live
- **THEN** it leaves the existing session running, and the new setting applies
  on the next session start.

### Requirement: the dev container hostname names its launcher

Claude Remote Control names its environment after the container hostname, and no
Claude option overrides that name. `devcontainer-init.sh` SHALL write
`CONTAINER_HOSTNAME` to the Compose `.env`, and the `devcontainer` service SHALL
take its `hostname` from it. The init script SHALL derive the value itself,
reading no file under `.devcontainer/scripts/`, which a consumer migrated to the
agentdev image does not keep. It checks, in this order of precedence:

- `coder-<CODER_WORKSPACE_NAME>` when `CODER_WORKSPACE_NAME` is set;
- `vscode-<host>-<checkout>` when `VSCODE_PID` or `VSCODE_IPC_HOOK` is set,
  which the VS Code extension host exports to the initialize command;
- `cli-<host>-<checkout>` otherwise.

`<host>` is the launching machine's hostname without its domain, and
`<checkout>` is the base name of the checkout directory. The value SHALL be one
RFC 1123 label: lowercase, every run of other characters replaced by one hyphen,
no leading or trailing hyphen, and at most 63 characters. Without the initialize
command's value, the `devcontainer` service SHALL take the hostname `agentdev`.
The hostname SHALL NOT change the Remote Control session name.

#### Scenario: a Coder workspace starts the dev container

- **WHEN** the initialize command runs with `CODER_WORKSPACE_NAME=agent-dev2`
- **THEN** the container hostname, and so the Remote Control environment name,
  is `coder-agent-dev2`, whatever VS Code variables Coder also sets.

#### Scenario: VS Code on a laptop starts the dev container

- **WHEN** VS Code on `Antons-MBP.local` opens the `agent-devcontainer` checkout
  in a container
- **THEN** the hostname is `vscode-antons-mbp-agent-devcontainer`.

#### Scenario: the devcontainer CLI starts the dev container

- **WHEN** `devcontainer up` runs on `builder` for the `agent-devcontainer`
  checkout outside VS Code and Coder
- **THEN** the hostname is `cli-builder-agent-devcontainer`.

#### Scenario: Compose runs without the initialize command

- **WHEN** `docker compose up` creates the `devcontainer` service with no
  `CONTAINER_HOSTNAME` in its environment or `.env`
- **THEN** the hostname is `agentdev`.

#### Scenario: one launcher opens the same checkout twice on one machine

- **WHEN** the same launcher on the same machine creates two containers for
  checkouts with the same directory name
- **THEN** both containers get the same hostname, and so the same Remote Control
  environment name.

### Requirement: Remote Control inherits the Coder agent's environment

The Claude process in `claude-remote` SHALL receive the environment of the
process that ran `agentdev-runtime remote-control start`, including when another
tmux server is live on the default socket. Started by the `coder_script`, it
SHALL carry the Coder user secrets and the agent's git credential helper.

#### Scenario: a GitHub token is a Coder user secret

- **WHEN** the workspace owner has a `GITHUB_TOKEN` env user secret and the
  `coder_script` starts `claude-remote`
- **THEN** `gh auth status` succeeds from the Remote Control session.

#### Scenario: a default tmux server is already running

- **WHEN** a tmux server is live on the default socket before the command runs
- **THEN** `claude-remote` starts on its own server and its Claude process
  receives the command's environment.

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

#### Scenario: the CI responder runs the lifecycle commands

- **WHEN** `agentdev-runtime lifecycle created` runs with
  `AGENTDEV_SKIP_CLAUDE_PREAPPROVE` set
- **THEN** neither `~/.claude.json` nor `.claude/settings.local.json` is
  modified.

## Rationale

### The autostart gate reads the live login status

The gate requires `authMethod: "claude.ai"` in addition to `loggedIn`, because a
setup-token login cannot run Remote Control. It reads
`claude auth status --json` rather than the credential file, because a rejected
refresh leaves a non-empty file with emptied tokens.

### Remote Control runs on its own tmux server

tmux gives a new session its server's global environment and copies from the
client only the `update-environment` variables. Remote Control therefore runs on
a dedicated server, `tmux -L claude-remote`, that the start command itself
starts, so the Claude process inherits the caller's environment even when
another tmux server is live on the default socket.

### No Dev Container lifecycle hook starts Remote Control

Rejected:

- **Keeping a post-start entry and having one entry yield to the other.**
  Post-start always runs first in Coder, so the generic entry would need a Coder
  signal it cannot observe before the agent exists, or the Coder entry would
  have to kill a live session it did not start.

### Pre-approval has an opt-out the CI responder sets

Pre-approval enables every project MCP server through
`enableAllProjectMcpServers`, which the headless CI responder must not inherit,
so `AGENTDEV_SKIP_CLAUDE_PREAPPROVE` skips it.

Rejected:

- **No opt-out.** It enables every project MCP server in the responder.
- **Gating on `AGENTDEV_SKIP_XPRA`.** That variable names the remote desktop,
  not headlessness.

### Session mode resumes one pinned conversation per volume

The pane resumes the conversation whose ID is stored on the `agentdev-claude`
volume, and falls back to a new pinned conversation on any non-zero resume exit.
Claude Code's transcript records the claude.ai session a conversation is bound
to, so resuming the conversation reattaches the same session URL, and Claude
Code mints a fresh remote session itself when the recorded one is gone or
belongs to another account. A resume whose transcript is gone exits non-zero,
which is the case the fallback covers; its cost is that a crash of a resumed
session also starts a fresh conversation. The pin hook reaches the pane alone
through `claude --settings`, and `/clear` moves the binding to the new
conversation, which is why the hook rewrites the stored ID on every
`SessionStart`. One stored ID per volume suffices because each devcontainer
instance has one workspace folder.

Rejected:

- **Checking for the transcript file before resuming.** It depends on Claude
  Code's undocumented transcript layout.
- **`claude --continue`.** It exits non-zero in a directory with no
  conversation, and otherwise takes the newest conversation in the directory,
  which can be an operator's terminal session.
- **A post-start health check for Remote Control.** No documented interface
  reports that a running session has Remote Control off; a check would read
  Claude Code's debug log or transcript, which can change without notice.
- **A pin hook in the repository's `.claude/settings.json`, gated on a variable
  the pane exports.** Every Claude session in the repository would run it.
- **Pinning the newest transcript at boot.** It depends on the undocumented
  transcript layout and can select an operator's terminal session.

### Server mode is an opt-in next to the pinned pane

`AGENTDEV_CLAUDE_RC_MODE=server` opts into `claude remote-control`; session mode
stays the default because the server resumes sessions only for about four hours
after it stops, which an overnight workspace stop exceeds, while the pinned pane
keeps its conversation indefinitely. The server refuses `--settings`, so it
cannot carry the pin hook, and without `--spawn` it stops at an interactive
spawn-mode prompt, so the start always passes `--spawn`. The maintainer made
`worktree` the default spawn mode, independently of how a worktree session
revives, and chose a failed startup for an unrecognized mode or spawn value, so
a typo is reported rather than silently running another mode.

Rejected:

- **Replacing the pinned pane with the server.** The four-hour resume window
  loses the conversation across an overnight stop.
- **Running a server next to the pinned pane.** It doubles the Remote Control
  entries and the processes that refresh the login, before it is known whether
  concurrent processes race the OAuth refresh token.
- **Folding the spawn mode into `AGENTDEV_CLAUDE_RC_MODE`** (for example
  `server-same-dir`). It merges two independent choices into one value list that
  grows with every spawn mode.
- **A pass-through argument variable.** It would accept `--continue` or
  `--settings`, which server mode refuses and which end the pane.
- **Offering `--spawn session`.** Its name collides with
  `AGENTDEV_CLAUDE_RC_MODE=session`, and it serves one session and exits when
  that ends, which ends the pane.
- **Falling back to session mode on an unrecognized value.** A mistyped mode
  would silently run the other mode.

### Server mode starts without `--continue`

A restarted server already reattaches the session it pre-created, and the
sessions it spawned on demand return through the claude.ai service's dispatch,
so server mode starts without `--continue`.

Rejected:

- **Starting the server with `--continue`.** Claude Code refuses it alongside
  `--spawn`, which ends the pane, and on its own it runs a single session that
  spawns nothing and leaves the spawned sessions disconnected.

### A spawn-mode switch is not worked around

A server revives every earlier session in its own current spawn mode, so after a
switch from `worktree` to `same-dir` the former worktree sessions work in the
workspace folder, and their worktrees and branches stay on disk unused. The
maintainer accepted this as a limit of switching the spawn mode, because the
spawn mode is not switched in production.

### The environment name says where a dev container came from, not which one

The hostname rule tells launchers and machines apart, not containers: two
containers of the same checkout opened by the same launcher on one machine share
an environment name, and a container that is not recreated keeps the name it was
created with. The rule covers only the Compose dev container; the standalone and
deploy runtimes are not named by it.
