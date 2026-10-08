---
type: architecture
description: How an agent drives long `codex exec` runs inside the devcontainer — full access, sequential runs under a shared usage quota, resuming an interrupted session in place, and scheduling the resume for the quota reset.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-06T09:00:00Z
---

# Headless Codex runs

This covers runs where one agent launches `codex exec` non-interactively and
needs the result: replays, batch reviews, and any multi-agent Codex job that
outlives a single turn. Codex's own configuration for interactive sessions is
[Configure devcontainer Codex for full access](../plans/20261005-codex-full-access-config.md).

## Access

The devcontainer is the isolation boundary, so a headless run gets full access:
`codex exec --dangerously-bypass-approvals-and-sandbox`. `codex exec` never
prompts, so anything short of full access fails the action instead of asking:

- **`--sandbox read-only` or `workspace-write`** — MCP tool calls that need
  approval fail with "requires approval, but approval policy is never", so a
  review loses the codebase-memory graph, and writes outside the workspace fail.
- **`--approve-for-me`** — routes approvals through Codex's automatic reviewer
  under the workspace-write sandbox; a weaker substitute, not full access.

Claude Code's auto mode refuses to write the bypass flag into a script on its
own. The maintainer adds the flag, or grants a permission rule for the runner
script. Even with full access, Codex's command guard rejects `rm -f`-style
commands, so a prompt never relies on the run deleting its own scratch files.

## Invocation

- **Close stdin.** `codex exec` reads a non-terminal stdin as more prompt input,
  so a background job or `xargs` feeds it whatever is attached. Run it with
  `</dev/null`.
- **Keep sessions.** Omit `--ephemeral`. Each session is recorded under
  `~/.codex/sessions/YYYY/MM/DD/rollout-*-<thread-id>.jsonl`, subagent sessions
  included, with each one's model. The `--json` event stream shows only the
  orchestrator: subagent dispatch appears as `wait` calls, so the rollouts are
  the record of what each pass and validator did.
- **Read the session id from the stream.** The first `--json` event is
  `{"type":"thread.started","thread_id":"<id>"}`; save the stream per run.
- **Treat only the final message as the result.** With `--output-schema`, every
  agent message is forced into the schema, so interim status updates appear as
  schema-valid objects with empty arrays. The `--output-last-message` file holds
  the last one; check that it carries content before scoring it.

## Usage limits

One account's quota is shared by every concurrent `codex exec` and every
subagent each one spawns. Hitting it ends the turn with an `error` event, then
`turn.failed`, whose message reads "You've hit your usage limit … try again at
<time>".

- **Run one at a time.** Parallel multi-agent runs draw on the quota together
  and fail together, keeping nothing. Sequential runs bank each finished result
  before the limit lands.
- **Detect the limit from the log**, not the exit status: grep the run's
  `--json` stream for `usage limit` and stop the sequence there.
- **Take the reset time from the message.** It may omit the date and time zone;
  compare it with `date` before scheduling.

## Resuming an interrupted run

A run stopped by the limit resumes in its own session rather than restarting:

``` bash
codex exec resume \
  --dangerously-bypass-approvals-and-sandbox \
  --model <same model> --config 'model_reasoning_effort="<same>"' \
  --output-schema <same schema> --output-last-message <same result file> \
  --json "<thread-id>" "<continue prompt>" </dev/null >"<new log>"
```

- `resume` takes no `--cd`; run it from the original working directory.
- Pass the same model, reasoning, access, and output flags rather than relying
  on the resumed session to carry them.
- The continue prompt tells the orchestrator to collect outstanding pass and
  validator results and finish. Subagent threads are their own sessions; the
  resumed orchestrator gathers or re-dispatches them.
- The `--json` redirect overwrites the log, which is the runner's record of the
  thread id. Rotate it to a numbered file before resuming.
- A runner script that clears its outputs before starting must never run on a
  resumable job; the resume path goes through its own script.

A driver over a fixed list of runs handles each in order: a run with a
contentful result and no limit in its log is complete and skipped; a run whose
log holds a thread id is resumed; any other run starts fresh. It stops at the
first limit and prints the reset time.

## Scheduling the resume

From Claude Code, schedule a one-shot `CronCreate` job a few minutes after the
reset, in local time, whose prompt runs the driver and states what to do with
the results. The job is session-only: it fires only while that Claude session is
open and idle, so it can miss its time. After the reset, check whether it ran;
if not, delete it so it cannot fire late, and run the driver directly.

Wait on a background run through its completion notification. A shell loop
polling `pgrep -f <script>` never ends when its own command line contains that
script name, because it matches itself.
