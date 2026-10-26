---
type: architecture
description: AGENTDEV_CLAUDE_RC_MODE=server opts the claude-remote pane into `claude remote-control` in place of the pinned interactive pane, which stays the default; AGENTDEV_CLAUDE_RC_SPAWN picks the worktree (default) or same-dir spawn mode, and an unrecognized value of either fails startup.
generated:
  by: claude-code/opus-5
  at: 2026-10-26T03:10:00Z
sources:
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: https://code.claude.com/docs/en/remote-control
- resource: https://code.claude.com/docs/en/claude-projects
- resource: https://code.claude.com/docs/en/worktrees
---

# Claude Remote Control server mode

## Decision

The maintainer decided that Remote Control server mode is an opt-in trial run
next to the pinned pane of [Claude Remote Control
resume](claude-remote-control-resume.md), which stays the default.
`AGENTDEV_CLAUDE_RC_MODE=server` makes `claude-remote-control-start.sh` run
`claude remote-control --spawn <spawn mode>` in the `claude-remote` tmux
session, passing `--name` and `--remote-control-session-name-prefix` set to
`CODER_WORKSPACE_NAME` when it is set. Unset or `session` keeps the pinned pane.
Any other value fails startup before any other check, printing the value and the
valid options.

The maintainer decided that server mode spawns each on-demand conversation in
its own git worktree by default: unset or `AGENTDEV_CLAUDE_RC_SPAWN=worktree`
passes `--spawn worktree`, and `AGENTDEV_CLAUDE_RC_SPAWN=same-dir` passes
`--spawn same-dir`, where every spawned conversation works in the workspace
folder. The session the server pre-creates works in the workspace folder in both
spawn modes. The spawn value is read only in server mode; there, any other value
fails startup right after the mode check, printing the value and the valid
options. Session mode ignores it.

The server runs on the same `tmux -L claude-remote` server, behind the same
claude.ai login gate and live-session reuse, and without
`CLAUDE_CODE_OAUTH_TOKEN`, as the pinned pane. It uses neither the pin hook nor
the stored conversation ID.

## Claude Code behavior the decision relies on

Measured on Claude Code 2.1.309, in `claude remote-control` server mode:

- **`--settings` is refused.** The server cannot receive the pane-only pin hook.
- **The spawn mode must be given.** Without `--spawn` and without a saved
  choice, the server stops at an interactive spawn-mode prompt, so the start
  script always passes `--spawn`.
- **No further confirmation is needed.** The preapproved workspace trust and
  Remote Control confirmation that the pinned pane uses suffice for the server.
- **Each session is a child `claude` process.** It inherits the server's
  environment, Coder user secrets and git credentials included, and has access
  to the credential store.
- **The pre-created session survives a restart.** After the server restarts, the
  session it created at start returns under the same ID with its earlier turns,
  and after a `/clear` in it, with the post-clear conversation.

Measured on Claude Code 2.1.310, across a devcontainer rebuild and a server
restart:

- **A spawned session returns after a restart in either spawn mode.** It comes
  back under the same ID with its earlier turns once the claude.ai service
  dispatches it, which can take minutes; see [Claude Remote Control server
  restart resume](claude-remote-control-server-restart-resume.md) for `same-dir`
  and [Claude Remote Control worktree restart
  resume](claude-remote-control-worktree-restart-resume.md) for `worktree`.
- **A revived worktree session re-enters its worktree.** The rebuild keeps the
  worktree and its branch, and the revived process runs in it.

Documented limits of server mode:

- Sessions are resumed only for about four hours after the server stops.
- The server exits after about ten minutes offline, and Remote Control stays off
  until the next agent start.
- Worktree mode needs a git repository, creates each worktree under
  `.claude/worktrees/` of the workspace folder, and keeps the pre-created
  session in the workspace folder.

## Rejected alternatives

- **Replacing the pinned pane.** An overnight workspace stop exceeds the
  four-hour resume window, losing the conversation the pinned pane keeps
  indefinitely.
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
- **Making the worktree default depend on a measured worktree revival.** The
  maintainer made worktree the default independently of how a worktree session
  revives.
- **Falling back to session mode on an unrecognized value.** The maintainer
  chose a failed startup, so a mistyped mode is reported instead of silently
  running the other mode.

## Consequences

- A mode or spawn-mode change does not affect a live `claude-remote` session; it
  applies on the next session start.
- `.claude/worktrees/` is gitignored, so spawned worktrees do not show up as
  untracked files in the workspace folder.
- Nothing restarts the server after it exits on an extended outage.
