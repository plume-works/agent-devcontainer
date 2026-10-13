---
type: feature
stage: proposed
status: draft
description: The autostarted Claude Remote Control resumes one pinned conversation per agentdev-claude volume, so a workspace restart or rebuild reattaches the same claude.ai/code session with its history.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-13T09:00:00Z
sources:
- resource: .devcontainer/scripts/claude-remote-control-session.sh
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: .devcontainer/devcontainer.json
- resource: https://code.claude.com/docs/en/remote-control
---

# Resume the Remote Control conversation across restarts

## Purpose

A Coder workspace starts Claude Remote Control unattended on every agent start.
Starting a fresh conversation each time would add a new claude.ai/code session
per restart or rebuild and take the previous chat offline for good. Resuming one
pinned conversation keeps a single session per workspace, with its history.

## Behaviour

**One pinned conversation per volume.** The `claude-remote` pane resumes the
conversation whose ID is stored in `remote-control-session-id` under Claude's
configuration directory, on the per-instance `agentdev-claude` volume. The
resume reattaches the same claude.ai/code session URL.

**First start pins a new conversation.** With no stored ID, the pane starts a
new conversation under a newly generated ID and stores that ID.

**A failed resume starts over.** When resuming exits non-zero, the pane starts a
new conversation under a new ID, which replaces the stored one.

The requirement and its scenarios live in [Claude Remote
Control](../spec/claude-remote-control.md); the decision and the Claude Code
behavior it relies on live in [Claude Remote Control
resume](../architecture/claude-remote-control-resume.md).

## Edge cases

- **Volume removed.** Removing `agentdev-claude` loses both the stored ID and
  the conversation; the next start pins a new one.
- **Transient reconnect failure.** Claude keeps running with Remote Control off;
  running `/remote-control` in the session restores it. Nothing detects this
  state automatically.
- **Any non-zero exit of a resumed session**, a crash included, starts a fresh
  conversation on the next start.

## Open questions

- **Downtime limit.** Resume holds after 4.5 hours with no process; whether it
  holds across a longer outage is unmeasured. The fallback covers any limit, so
  the figure only sets how often a fresh conversation starts.
