---
type: adr
stage: accepted
description: Session mode resumes the one conversation whose ID a pin hook keeps in the Claude configuration directory on the home volume.
---

# Session mode resumes one pinned conversation

The pinned pane resumes the conversation whose ID it keeps in
`remote-control-session-id`, in the Claude configuration directory on the home
volume. A pin hook writes the ID again at each `SessionStart`, because `/clear`
moves the session to a new conversation. One ID for each home volume is
sufficient, because each instance has one workspace folder.

## Considered Options

- `claude --continue`. Rejected: it exits non-zero in a directory with no
  conversation. If not, it takes the newest conversation in the directory, which
  can be a terminal session of an operator.
- A check for the transcript file before the resume, or a pin on the newest
  transcript at container start. Rejected: both use the transcript layout of
  Claude Code, which has no documentation.
- A pin hook in `.claude/settings.json`, with a gate on a variable that the pane
  exports. Rejected: each Claude session in the repository runs it.
- A health check for Remote Control after the start. Rejected: no documented
  interface tells that Remote Control is off in a session that runs.

## Consequences

- Only the pane gets the pin hook, through `claude --settings`
  (`py_packages/agentdev_runtime/agentdev_runtime/remote_control.py::session`).
- A resume that exits non-zero starts a new pinned conversation. As a result, a
  crash of a resumed session also starts a new conversation.
- The transcript records the claude.ai session of the conversation, so a resume
  uses the same session URL again while that session exists for the account.
