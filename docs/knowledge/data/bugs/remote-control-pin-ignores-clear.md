---
type: bug
description: The pinned Remote Control conversation ID is written only when the claude-remote pane starts, so after a /clear a workspace restart resumes the pre-clear conversation and Claude Code mints a new claude.ai session URL for it.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-21T01:40:00Z
sources:
- resource: .devcontainer/scripts/claude-remote-control-session.sh
- resource: docs/knowledge/data/spec/claude-remote-control.md
- resource: docs/knowledge/data/architecture/claude-remote-control-resume.md
- resource: https://code.claude.com/docs/en/hooks
---

# Bug: the Remote Control pin ignores `/clear`

## Symptom

[Claude Remote Control](../spec/claude-remote-control.md) has the
`claude-remote` pane resume the conversation stored in
`remote-control-session-id`. Running `/clear` in the pane starts a new
conversation in the same process, and the claude.ai/code session follows it, but
the stored ID still names the pre-clear conversation. On the next workspace
restart the pane resumes the pre-clear conversation, and because its remote
session now belongs to the post-clear one, Claude Code mints a fresh claude.ai
session for it. The operator lands in the wrong conversation under a new session
URL, and the post-clear conversation is no longer reachable from claude.ai/code.

## Reproduction

On Claude Code 2.1.304, in a Coder workspace whose `claude-remote` pane is
running:

1. Note the stored ID: `cat ~/.claude/remote-control-session-id` (call it A).
2. From claude.ai/code, run `/clear` in the session and send a prompt. The pane
   now writes a new transcript B, and B's `bridge-session` record names the same
   `cse_…` remote session that A held.
3. `remote-control-session-id` still contains A.
4. Restart the workspace. The pane runs
   `claude --remote-control <name> --resume A`; A's transcript gains a
   `bridge-session` record with an empty `bridgeSessionId`, then one with a new
   `cse_…` ID.

Expected: the pane resumes B under the original session URL. Observed: it
resumes A under a new one.

## Root cause

`claude-remote-control-session.sh` writes the ID file only before it launches
Claude: on a missing ID or a failed resume. Nothing updates it while Claude
runs, so any in-process change of conversation — `/clear`, and equally `/resume`
of another conversation — leaves the pin stale. The spec's requirement assumes
the pane's conversation is fixed for the life of the process and has no scenario
for one that changes.

The post-clear transcript does record the moved remote session binding, so
resuming B would reattach the original URL; the defect is only in which ID is
pinned.

## Fix

Open. The fix is a `SessionStart` hook that writes the event's `session_id` to
`remote-control-session-id`, supplied only to the pane through
`claude --settings` in `claude-remote-control-session.sh` so operator sessions
never overwrite the pin.

Measured on Claude Code 2.1.304 in interactive `--remote-control` mode, a hook
supplied through `--settings` runs and fires with `source` `startup`, `clear`,
and `resume`. On `clear` its `session_id` is the new conversation's ID, and the
pre-clear transcript's `bridge-session` record is emptied as the binding moves.
Resuming the ID the hook recorded reattaches the original claude.ai session URL.

The spec gains a scenario: WHEN `/clear` runs in `claude-remote` and the
workspace restarts, THEN the post-clear conversation resumes under the same
session URL.

## Key references

Verified anchor points (line numbers as of 2026-10-21):

- `.devcontainer/scripts/claude-remote-control-session.sh:5` — `id_file`, the
  pin's path.
- `.devcontainer/scripts/claude-remote-control-session.sh:15` — the resume of
  the stored ID.
- `.devcontainer/scripts/claude-remote-control-session.sh:21` — the only write
  of the pin, before `exec claude`.
- `docs/knowledge/data/spec/claude-remote-control.md:51` — the requirement that
  the pane resume the stored ID.
- `docs/knowledge/data/architecture/claude-remote-control-resume.md:27` — "The
  transcript carries the binding."
