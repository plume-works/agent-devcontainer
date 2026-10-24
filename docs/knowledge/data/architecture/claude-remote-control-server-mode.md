---
type: architecture
description: AGENTDEV_CLAUDE_RC_MODE=server opts the claude-remote pane into `claude remote-control --spawn same-dir` in place of the pinned interactive pane, which stays the default; an unrecognized value fails startup.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-24T02:07:30Z
sources:
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: https://code.claude.com/docs/en/remote-control
- resource: https://code.claude.com/docs/en/claude-projects
---

# Claude Remote Control server mode

## Decision

The maintainer decided that Remote Control server mode is an opt-in trial run
next to the pinned pane of [Claude Remote Control
resume](claude-remote-control-resume.md), which stays the default.
`AGENTDEV_CLAUDE_RC_MODE=server` makes `claude-remote-control-start.sh` run
`claude remote-control --spawn same-dir` in the `claude-remote` tmux session,
passing `--name` and `--remote-control-session-name-prefix` set to
`CODER_WORKSPACE_NAME` when it is set. Unset or `session` keeps the pinned pane.
Any other value fails startup before any other check, printing the value and the
valid options.

`same-dir` is the only spawn mode: every spawned conversation works in the
workspace folder. The server runs on the same `tmux -L claude-remote` server,
behind the same claude.ai login gate and live-session reuse, and without
`CLAUDE_CODE_OAUTH_TOKEN`, as the pinned pane. It uses neither the pin hook nor
the stored conversation ID.

## Claude Code behavior the decision relies on

Measured on Claude Code 2.1.309, in `claude remote-control` server mode:

- **`--settings` is refused.** The server cannot receive the pane-only pin hook.
- **The spawn mode must be given.** Without `--spawn` and without a saved
  choice, the server stops at an interactive spawn-mode prompt, so the start
  script always passes `--spawn same-dir`.
- **No further confirmation is needed.** The preapproved workspace trust and
  Remote Control confirmation that the pinned pane uses suffice for the server.
- **Each session is a child `claude` process.** It inherits the server's
  environment, Coder user secrets and git credentials included, and has access
  to the credential store.
- **The pre-created session survives a restart.** After the server restarts, the
  session it created at start returns under the same ID with its earlier turns,
  and after a `/clear` in it, with the post-clear conversation.
- **A spawned worktree session does not survive a restart.**

Documented limits of server mode:

- Sessions are resumed only for about four hours after the server stops.
- The server exits after about ten minutes offline, and Remote Control stays off
  until the next agent start.

## Rejected alternatives

- **Replacing the pinned pane.** An overnight workspace stop exceeds the
  four-hour resume window, losing the conversation the pinned pane keeps
  indefinitely.
- **Running a server next to the pinned pane.** It doubles the Remote Control
  entries and the processes that refresh the login, before it is known whether
  concurrent processes race the OAuth refresh token.
- **`--spawn worktree`.** A spawned worktree session does not survive a server
  restart, which is exactly what server mode brings back.
- **Falling back to session mode on an unrecognized value.** The maintainer
  chose a failed startup, so a mistyped mode is reported instead of silently
  running the other mode.

## Consequences

- A mode change does not affect a live `claude-remote` session; it applies on
  the next session start.
- Nothing restarts the server after it exits on an extended outage.
