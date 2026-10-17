---
type: someday
description: Have postAttachCommand.sh signal long-running harness sessions started by the Coder agent through a marker file, so every harness restarts onto the catalog it just re-registered.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-17T00:00:00Z
sources:
- resource: .devcontainer/scripts/postAttachCommand.sh
- resource: .devcontainer/scripts/coder-agent-start.sh
---

# Restart Coder-started harness sessions after a catalog refresh

`postAttachCommand.sh` re-registers the agentdev catalog for every harness —
Codex, Claude, and OpenCode — on each editor attachment. Sessions that the Coder
agent started earlier, such as Claude Remote Control and the [OpenCode web
UI](../features/opencode-web-coder-autostart.md), read their configuration when
they started, so they can keep serving the previous catalog until they restart.

The idea: `postAttachCommand.sh` touches one marker file after the reinstall
scripts finish, and each Coder-started session watches it — `inotifywait`, or a
polling loop beside the process in its tmux session — and restarts its process
when the marker changes. One signal covers every harness, present and future.

Open questions:

- Which harnesses actually keep a stale catalog. A harness that rescans its
  plugin and skill directories per session needs no restart.
- Whether a restart may interrupt a conversation in progress: Remote Control
  resumes its pinned conversation, but an OpenCode request in flight would be
  cut off.
- Whether a restart should wait until the session is idle.
