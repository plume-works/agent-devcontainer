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

#### Scenario: the mode or spawn mode changes while a session is live

- **WHEN** the command runs with a different mode or spawn mode while
  `claude-remote` is live
- **THEN** it leaves the existing session running, and the new setting applies
  on the next session start.

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

The pane resumes the conversation whose ID is stored in Claude's configuration
directory on the per-instance home volume `agentdev-home-${devcontainerId}`, and
falls back to a new pinned conversation on any non-zero resume exit. Claude
Code's transcript records the claude.ai session a conversation is bound to, so
resuming the conversation reattaches the same session URL, and Claude Code mints
a fresh remote session itself when the recorded one is gone or belongs to
another account. A resume whose transcript is gone exits non-zero, which is the
case the fallback covers; its cost is that a crash of a resumed session also
starts a fresh conversation. The pin hook reaches the pane alone through
`claude --settings`, and `/clear` moves the binding to the new conversation,
which is why the hook rewrites the stored ID on every `SessionStart`. One stored
ID per volume suffices because each devcontainer instance has one workspace
folder.

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
