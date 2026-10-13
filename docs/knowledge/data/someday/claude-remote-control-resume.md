---
type: someday
description: Resume the autostarted Remote Control conversation by a pinned session ID so a restart or rebuild reattaches the same claude.ai/code session; measured on Claude Code 2.1.296, with lost-session detection still open.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-13T02:25:00Z
sources:
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: .devcontainer/devcontainer.json
- resource: https://code.claude.com/docs/en/remote-control
---

# Resume the Remote Control conversation across restarts

`claude-remote-control-start.sh` starts a fresh `claude --remote-control`
conversation every time, so each workspace restart or rebuild adds a new
claude.ai/code session and the previous chat stops receiving work. Resuming the
previous conversation instead would keep one session per workspace. See [Claude
Remote Control](../spec/claude-remote-control.md) for the current contract.

## Measured behavior

Claude Code 2.1.296, interactive `--remote-control` mode, in a scratch directory
with its own conversation history:

- **The link lives in the local transcript.** The conversation `.jsonl` records
  a `bridge-session` entry carrying the claude.ai `bridgeSessionId`.
  `~/.claude/projects/` is on the per-instance `agentdev-claude` volume, so the
  record survives a container restart and a rebuild, not a volume removal.
- **`claude --resume <uuid>` reattaches the same session.** It reconnects to the
  recorded `bridgeSessionId`, and new turns are delivered to it. Adding
  `--remote-control <name>` to the resume is harmless: it reattaches the same
  session rather than registering a second one. `--remote-control` is not needed
  for the reattach.
- **Either kind of stop resumes.** A graceful exit archives the remote session;
  the resume unarchives it. A `SIGKILL` leaves it unarchived, and the resume
  reattaches directly.
- **Four and a half hours of downtime still resumes.** After a `SIGKILL`
  followed by 4.5 hours with no process, the resume reattached the same session.
  The documented four-hour server-mode window does not bound interactive
  sessions at that length; the actual limit is unmeasured.
- **`--session-id <uuid>` pins the conversation ID** at first start, so the ID
  to resume is known without searching.
- **`--continue` is unusable for autostart.** With no prior conversation in the
  directory it prints `No conversation found to continue` and exits 1, with or
  without `--remote-control`. With history, it takes the newest conversation in
  the directory, which can be an operator's terminal session rather than the
  Remote Control one.
- **`--resume` without an ID opens an interactive picker**, which a detached
  tmux pane cannot answer.

## Shape

``` text
no stored ID      → uuid=new; store on agentdev-claude
                    claude --remote-control <name> --session-id "$uuid"
stored ID         → claude --remote-control <name> --resume "$uuid"
session gone      → new uuid, fresh start (needs detection, below)
```

## Promotion criteria

- **Downtime limit.** Resume holds past 4.5 hours; whether it holds across a
  longer outage, such as a workspace stopped over a weekend, is unmeasured. The
  fallback below covers any limit, so the figure matters only for how often the
  fallback fires.
- **Detecting a lost session.** When the server-side session is gone, the
  documentation says Claude Code shows `Previous session is unavailable` and
  keeps running with Remote Control off, instead of starting a new session. An
  unattended start must detect that state and fall back to a fresh start;
  otherwise a live `claude` pane with Remote Control off violates the spec's
  `/rc active` scenario. How the script observes the state is unsolved.
- **Concurrent resume.** A second process resuming the same conversation while
  the first holds Remote Control leaves Remote Control off in the second; the
  existing single-tmux-session guard already prevents that case.
