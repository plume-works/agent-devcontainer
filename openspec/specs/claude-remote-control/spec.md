# Claude Remote Control Specification

## Purpose

Claude Remote Control autostarts from the Coder agent, or from the standalone runtime's supervised watcher when AGENTDEV_CLAUDE_RC_MODE opts in, only on a live claude.ai login, inheriting the agent's environment and either resuming its pinned conversation or, opted in with AGENTDEV_CLAUDE_RC_MODE=server, running a spawn-on-demand server that gives each spawned conversation its own git worktree unless AGENTDEV_CLAUDE_RC_SPAWN=same-dir, every container pre-approves Claude's first-run state unless it opts out, and the dev container's hostname, which names the Remote Control environment, says where the container came from.

Claude credentials come only from a `/login` inside a container, persisted in
the shared `agentdev-agents-auth` volume ([Agent auth
persistence](../devcontainer-state/spec.md)). On top of that login,
a Coder workspace starts Claude Remote Control unattended under the Coder agent,
the standalone `agentdev-deploy` runtime starts it when
`AGENTDEV_CLAUDE_RC_MODE` opts in, and every devcontainer answers Claude's
first-run prompts ahead of time.

## Requirements

### Requirement: Remote Control autostarts only on a live claude.ai login

`agentdev-runtime remote-control start` SHALL start Remote Control in exactly
one detached tmux session named `claude-remote`, on the dedicated tmux server
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
- **THEN** no session is started and the command exits successfully.

#### Scenario: only a setup token is available

- **WHEN** `claude auth status --json` reports `loggedIn: true` with an
  `authMethod` other than `claude.ai`
- **THEN** no session is started.

#### Scenario: the operator logs in after the workspace started

- **WHEN** an operator completes `/login` and runs the command from a Coder
  terminal
- **THEN** `claude-remote` starts without a workspace restart.

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
`claude-remote` session SHALL run `claude remote-control --spawn <spawn mode>`,
passing `--name` and `--remote-control-session-name-prefix` set to
`CODER_WORKSPACE_NAME` when it is set, and SHALL neither read nor write the
stored conversation ID. `.claude/worktrees/` SHALL be ignored by git.

#### Scenario: server mode is selected

- **WHEN** the command starts `claude-remote` with
  `AGENTDEV_CLAUDE_RC_MODE=server` and `AGENTDEV_CLAUDE_RC_SPAWN` unset
- **THEN** the session runs `claude remote-control --spawn worktree` and reaches
  a connected server with no terminal interaction.

#### Scenario: same-dir spawn mode is selected

- **WHEN** the command starts `claude-remote` with
  `AGENTDEV_CLAUDE_RC_MODE=server` and `AGENTDEV_CLAUDE_RC_SPAWN=same-dir`
- **THEN** the session runs `claude remote-control --spawn same-dir`.

#### Scenario: a conversation is spawned in worktree mode

- **WHEN** a new conversation is started in the workspace's environment from
  claude.ai/code or the Claude mobile app while the server runs in worktree mode
- **THEN** it runs in its own git worktree under the workspace folder's
  `.claude/worktrees/` with the environment of the process that ran the command,
  and `git status` in the workspace folder lists none of its files.

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
no leading or trailing hyphen, and at most 63 characters.

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

### One pinned conversation per volume, the default

The maintainer decided that the `claude-remote` pane resumes one pinned
conversation per `agentdev-claude` volume, one being enough because each
devcontainer instance has one workspace folder. The pin hook is supplied only to
the pane through `claude --settings`, so no other Claude session in the
repository runs it. Any non-zero exit of a resume starts a fresh conversation,
a crash included; that is the accepted cost of not reading Claude Code's
transcript layout. A transient reconnect failure stays a known limitation with
no health check.

Claude Code behavior the pin relies on, measured on 2.1.296 and 2.1.304: a
conversation's transcript records the claude.ai session it is bound to, and
resuming reattaches it; when that session is gone or the login belongs to
another account, the resume mints a fresh session and records it; a resume with
no transcript exits 1; a `--settings` `SessionStart` hook fires on `startup`,
`clear`, and `resume`, and on `clear` carries the new conversation's ID, so
resuming the recorded ID reattaches the original session URL.

Rejected:

- **Check for the transcript file before resuming.** It depends on Claude Code's
  undocumented transcript layout.
- **`claude --continue`.** It exits 1 with no conversation, and otherwise takes
  the newest one in the directory, which can be an operator's terminal session.
- **A post-start health check.** No documented interface reports that a session
  has Remote Control off.
- **A pin hook in `.claude/settings.json` gated on an environment variable.**
  Every Claude session in the repository would run it.
- **Pin the newest transcript at boot.** Undocumented layout, and it can pick an
  operator's session.

### Server mode is an opt-in trial

The maintainer decided that `claude remote-control` server mode runs only when
`AGENTDEV_CLAUDE_RC_MODE=server` opts in, that it spawns into a git worktree by
default, independently of how a worktree session revives, and that an
unrecognized mode or spawn value fails startup rather than silently running the
other mode. Claude Code 2.1.309 refuses `--settings` in server mode, so the
server cannot take the pin hook; without `--spawn` and a saved choice it stops at
an interactive prompt; each session is a child `claude` process with the
server's environment and credential store; and the pre-created session returns
under its ID after a restart. Documented limits: sessions resume only for about
four hours after the server stops, the server exits after about ten minutes
offline and nothing restarts it, and worktree mode needs a git repository.

`--continue` is incompatible with server mode: alongside `--spawn` it exits with
an error that ends the pane, and alone it runs a single session that spawns
nothing, while a restarted server already reattaches its pre-created session.
A revived session takes the reviving server's spawn mode, so after a switch
from `worktree` to `same-dir` former worktree sessions run in the workspace
folder; the maintainer accepts this, because the spawn mode is not switched in
production.

Rejected:

- **Replace the pinned pane.** An overnight workspace stop exceeds the four-hour
  resume window.
- **Run a server next to the pinned pane.** It doubles the Remote Control
  entries and the processes refreshing the login, before it is known whether
  they race the OAuth refresh token.
- **Fold the spawn mode into `AGENTDEV_CLAUDE_RC_MODE`.** It merges two
  independent choices into one growing value list.
- **A pass-through argument variable.** It would accept `--continue` or
  `--settings`, which end the pane.
- **Offer `--spawn session`.** Its name collides with
  `AGENTDEV_CLAUDE_RC_MODE=session`, and it exits when its one session ends.
- **Start the server with `--continue`.** Refused alongside server-mode flags.
