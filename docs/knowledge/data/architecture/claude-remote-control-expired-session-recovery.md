---
type: architecture
description: Once the claude.ai service deletes a stopped Remote Control server's environment, its sessions cannot be reopened from claude.ai or the Claude app, but their transcripts survive on the agentdev-claude volume and `claude --resume <id> --remote-control` brings each back with its history as a new claude.ai session.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-27T06:20:00Z
sources:
- resource: .devcontainer/devcontainer.json
- resource: https://code.claude.com/docs/en/remote-control
---

# Claude Remote Control expired session recovery

Finding against [Claude Remote Control server
mode](claude-remote-control-server-mode.md), measured on Claude Code 2.1.310
with `claude remote-control --spawn same-dir`.

## Measurement

- **The service deletes a stopped server's environment.** About four and a half
  hours after the server stopped, the bridge environment it had registered was
  gone from the account's environments, and every session on it carried a
  non-recoverable `environment_deleted` init error: "The environment this
  session was running on has been deleted; its state cannot be recovered."
- **Every session on that environment is lost to claude.ai**, the pre-created
  one and those spawned on demand alike. Opening one in the Claude app fails
  with "Couldn't start session. This session's repository couldn't be found."
- **A restarted server registers a new environment.** Its name carries the
  container hostname, and it does not adopt the sessions of the deleted one.
- **The transcripts survive.** Each conversation is a
  `~/.claude/projects/<cwd slug>/<transcript id>.jsonl` file on the
  `agentdev-claude` volume, which outlives container rebuilds. The transcript ID
  is a UUID, not the claude.ai `session_…` ID.
- **A transcript carries its claude.ai title** as `custom-title` records, so
  `grep -l '"customTitle":"<title>"' ~/.claude/projects/<cwd slug>/*.jsonl`
  finds the transcript of a session listed by name.

## Recovery

Run from the session's working directory, so the transcript resolves:

``` bash
tmux new-session -d -s <name> -c <workdir> \
  "claude --resume <transcript id> --remote-control '<display name>'"
```

- **The history returns.** The resumed conversation shows every earlier turn and
  accepts new ones.
- **It is a new claude.ai session.** It gets a new `session_…` ID and URL, which
  the pane prints, and keeps the title recorded in the transcript. The deleted
  session stays listed with its error until archived.
- **It is a single Remote Control session, not a server.** Nothing in the
  devcontainer starts it again after a restart, so a later outage needs the same
  recovery.
- **It runs in the current checkout.** A transcript that names a branch
  describes the checkout at the time; the resumed process sees whatever is
  checked out now.

## Hypotheses eliminated

- **A devcontainer rebuild deletes the sessions.** Eliminated as the cause: the
  deletion followed the server's stop by about four and a half hours, the
  documented resume window, independent of the rebuild.
- **The conversations are lost.** Eliminated: the transcripts stay on the volume
  and resume with their history.

## Open questions

- **Whether a rebuild inside the resume window keeps the sessions.** The
  restarted server registers an environment named after the new container
  hostname, so a rebuild may orphan them even before the window closes. Settling
  it takes a rebuild and a server restart within four hours of the stop, then
  checking whether the earlier sessions return.

## Closing

Recovery by hand is enough while server mode remains an opt-in trial. The
finding closes when the open question is measured, or when the maintainer
decides that automatic recovery of expired sessions is not worth building.
