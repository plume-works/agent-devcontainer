---
type: architecture
description: The autostarted Remote Control resumes one pinned conversation per agentdev-claude volume, keeps the pin on the pane's current conversation through a pane-only SessionStart hook, and falls back to a fresh pinned conversation on a non-zero resume exit; Claude Code itself mints a fresh remote session when the recorded one is gone or belongs to another account.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T04:32:14Z
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/remote_control.py
- resource: .devcontainer/devcontainer.json
- resource: https://code.claude.com/docs/en/remote-control
- resource: https://code.claude.com/docs/en/hooks
---

# Claude Remote Control resume

## Decision

The maintainer decided that the `claude-remote` tmux pane resumes one pinned
conversation per `agentdev-claude` volume. The conversation ID is stored on that
volume; a start with no stored ID, or whose resume exits non-zero, begins a new
conversation under a newly generated ID and stores it. A `SessionStart` hook,
supplied only to the pane's Claude process through `claude --settings`, rewrites
the stored ID whenever the pane's conversation changes, so `/clear` moves the
pin to the new conversation. A transient reconnect failure is a known limitation
with no health check.

## Claude Code behavior the decision relies on

Measured on Claude Code 2.1.296, in interactive `--remote-control` mode:

- **The transcript carries the binding.** Each conversation's transcript records
  the claude.ai session it is bound to. Resuming the conversation reattaches
  that session; `--remote-control <name>` on the resume reattaches the same
  session rather than registering another.
- **Claude Code recovers a lost remote session itself.** When the recorded
  remote session no longer exists, the resume mints a fresh Remote Control
  session for the same local conversation. When the login belongs to a different
  account than the one recorded, it also mints a fresh session and leaves the
  earlier turns out of it. In both cases the transcript records the new session,
  so the next resume targets it.
- **A missing transcript fails the resume.** `claude --resume <uuid>` with no
  transcript for that ID prints `No conversation found with session ID: <uuid>`
  and exits 1. Claude Code's transcript cleanup can therefore leave a stored ID
  that no longer resumes.
- **A transient reconnect failure leaves Remote Control off.** The Remote
  Control documentation describes
  `Couldn't reconnect to your Remote Control session` for a reconnect that fails
  for a possibly temporary reason; Claude Code keeps the local session running
  without Remote Control, and running `/remote-control` in it retries the
  connection.

Measured on Claude Code 2.1.304, in interactive `--remote-control` mode:

- **A `--settings` hook runs in the pane.** A `SessionStart` hook supplied
  through `--settings` fires with `source` `startup`, `clear`, and `resume`.
- **`/clear` moves the binding to the new conversation.** On `clear` the hook's
  `session_id` is the new conversation's ID, and the pre-clear transcript's
  binding is emptied. Resuming the pre-clear ID therefore mints a fresh remote
  session, while resuming the ID the hook recorded reattaches the original
  claude.ai session URL.

## Rejected alternatives

- **Checking for the transcript file before resuming.** It would distinguish a
  missing conversation from a crash, but it depends on Claude Code's
  undocumented transcript layout. The cost of the chosen exit-code fallback is
  that any non-zero exit of a resumed session, a crash included, starts a fresh
  conversation.
- **`claude --continue`.** It exits 1 in a directory with no conversation, and
  otherwise takes the newest conversation in the directory, which can be an
  operator's terminal session.
- **A post-start health check.** No documented interface reports that a running
  session has Remote Control off; a check would read Claude Code's debug log or
  transcript, which can change without notice.
- **A pin hook in the repository's `.claude/settings.json`, gated on an
  environment variable the pane exports.** Every Claude session in the
  repository would run it, where the `--settings` hook reaches only the pane.
- **Pinning the newest transcript at boot.** It depends on Claude Code's
  undocumented transcript layout and can select an operator's terminal session.

## Consequences

- Removing the `agentdev-claude` volume loses both the stored ID and the
  conversation; the next start begins a new one.
- One stored ID per volume suffices because each devcontainer instance has one
  workspace folder.
