---
type: adr
stage: accepted
description: AGENTDEV_CLAUDE_RC_MODE=server selects the `claude remote-control` server, session mode stays the default, and an unrecognized mode or spawn value stops the start.
---

# Server mode is an opt-in next to session mode

`AGENTDEV_CLAUDE_RC_MODE=server` selects the `claude remote-control` server, and
session mode stays the default. The server resumes sessions for only about four
hours after it stops, and a workspace stop for one night is longer. The pinned
pane keeps its conversation with no time limit. An unrecognized mode or spawn
value stops the start, so that an incorrect value does not run the other mode
with no message.

## Considered Options

- Replace the pinned pane with the server. Rejected: the four-hour limit does
  not keep the conversation after a stop for one night.
- Run a server next to the pinned pane. Rejected: it gives two Remote Control
  entries and two processes that refresh the single-use login token.
- Put the spawn mode into `AGENTDEV_CLAUDE_RC_MODE`, for example
  `server-same-dir`. Rejected: one list of values then holds two independent
  choices and grows with each spawn mode.
- A variable that sends its arguments to the server with no change. Rejected: it
  accepts `--continue` or `--settings`, which the server refuses, and the pane
  then stops.
- `--spawn session`. Rejected: its name is almost the same as
  `AGENTDEV_CLAUDE_RC_MODE=session`, and the pane stops when its one session
  ends.
- Start the server with `--continue`. Rejected: Claude Code refuses it with
  `--spawn`. A restarted server attaches its first session again, and the
  claude.ai service sends the spawned sessions back to it.

## Consequences

- The start checks the mode before each other check. It reads the spawn value
  only in server mode, and session mode ignores it.
- The server runs in the `claude-remote` session of the `tmux -L claude-remote`
  server, as the pinned pane does. It has the same claude.ai login check, it
  uses a live session again, and it gets no `CLAUDE_CODE_OAUTH_TOKEN`. When
  `CODER_WORKSPACE_NAME` is set, the start gives it as `--name` and
  `--remote-control-session-name-prefix`.
- A change of mode or spawn value does not change a live `claude-remote`
  session. It applies at the next start.
- The server refuses `--settings`, so it has no pin hook. The start always gives
  `--spawn`, because without it the server stops at a prompt. `worktree` is the
  default spawn mode, by decision of the maintainer.
- Claude Code, not this repository, sets where a conversation runs. The first
  session runs in the workspace folder. In `worktree` mode, each spawned
  conversation gets its own git worktree under `.claude/worktrees/`, which git
  ignores. Each conversation gets the environment of the start process and
  starts in the `auto` permission mode. As a result, each conversation has the
  Coder user secrets, the git credentials, and access to the credential store.
- A server starts each earlier session again in its current spawn mode. After a
  change from `worktree` to `same-dir`, the earlier sessions work in the
  workspace folder, and their worktrees and branches stay on disk. The
  maintainer accepted this limit, because production does not change the spawn
  mode.
- After a restart, a session that the server spawned comes back only when the
  claude.ai service sends it to the server, which can take minutes.
- The server stops after about ten minutes without a network connection, and
  nothing starts it again before the next agent start. About four hours after
  the server stops, the claude.ai service deletes its sessions. The transcripts
  stay on the home volume, and `claude --resume <id> --remote-control` starts
  each again as a new claude.ai session.
