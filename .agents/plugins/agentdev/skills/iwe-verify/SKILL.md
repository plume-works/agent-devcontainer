---
name: iwe-verify
description: Verify that implementation matches the graph — check a plan's tasks, spec requirements, and scenarios against the actual code before shipping, or sweep the whole workspace for doc↔code drift.
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/agent-code/*)
---

# Verify implementation against the graph

The Verify rulebook is the `iwe-verifier` catalog agent, and every Verify run
starts from a fresh context: whether the code matches the graph must rest on
what the code and the graph record, never on what a conversation asserted. This
skill routes the run there and keeps the last report per plan, so a caller on a
commit Verify already judged gets that verdict back without a second run. Pick
the route by where you are; both start and end at the cache.

## The saved report

[verify-cache.py](agent-code/verify-cache.py) keeps one saved report per plan,
and one for audit mode, keyed by the commit Verify ran on and the digest of the
active agentdev catalog. Run it from the repository root. Its target is the plan
key, or `audit` in audit mode.

**Look up** before any Verify step, adding `--fresh` only when the user's own
request carries it:

```bash
agent-code/verify-cache.py lookup <plan-key|audit> [--fresh]
```

| RESULT            | Exit   | Action                                                                                                                                 |
| ----------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| `HIT`             | `3`    | Read the file `REPORT` names and return its body, led by `Saved Verify report from <COMMIT>`. Run no Verify step.                      |
| `MISS`            | `4`    | Run Verify by your route, keeping `COMMIT` for the save.                                                                               |
| `DIRTY_WORKTREE`  | `5`    | **STOP.** Report that Verify runs only on a clean worktree, with the paths stderr lists. Commit or remove them, then run Verify again. |
| `PREFLIGHT_ERROR` | `2`    | **STOP.** Report the blocker verbatim (not a repository, no commit, bad arguments).                                                    |
| `SCRIPT_FAILURE`  | `1`    | **STOP.** Report the blocker verbatim; do not retry or work around it.                                                                 |
| `SIGNAL_*`        | `129`+ | **STOP.** The run was interrupted; report it.                                                                                          |

**Save** the report the run produced, verbatim on stdin, with the `COMMIT` the
miss printed, the verdict its lead line names — `Ready to ship`, `Blocked`, or
`Audit` — and two prompts, each verbatim, which the saved report records but
does not key on:

- **Skill request** — the request this skill was invoked with: the user's words
  on the session route, or the plan key and approvals the Implement loop or the
  Shipper invoked it with.
- **Verifier prompt** — the prompt the `iwe-verifier` rulebook ran under: the
  dispatch prompt on the session route, and on the Shipper's route the plan key
  and the approvals the Shipper's own prompt quotes, in the same form.

Never save a `Needs decision` report. The quoted heredocs pass every character
through literally:

```bash
agent-code/verify-cache.py save <plan-key|audit> --commit <COMMIT> \
  --verdict '<verdict>' \
  --skill-request "$(cat <<'SKILL_REQUEST'
<the skill request, verbatim>
SKILL_REQUEST
)" \
  --verifier-prompt "$(cat <<'VERIFIER_PROMPT'
<the verifier prompt, verbatim>
VERIFIER_PROMPT
)" <<'VERIFY_REPORT'
<the report, verbatim>
VERIFY_REPORT
```

| RESULT            | Exit   | Action                                                                                                              |
| ----------------- | ------ | ------------------------------------------------------------------------------------------------------------------- |
| `SUCCESS`         | `0`    | Return the report.                                                                                                  |
| `DIRTY_WORKTREE`  | `5`    | Return the report unsaved, and say the worktree was dirty after the run, so the next Verify will not reuse it.      |
| `HEAD_MOVED`      | `6`    | Return the report unsaved, and say `HEAD` moved off `COMMIT` during the run, so the report may not describe `HEAD`. |
| `PREFLIGHT_ERROR` | `2`    | Return the report unsaved, with the error verbatim.                                                                 |
| `SCRIPT_FAILURE`  | `1`    | Return the report unsaved, with the error verbatim.                                                                 |
| `SIGNAL_*`        | `129`+ | Return the report unsaved, and say the save was interrupted.                                                        |

## From inside `iwe-shipper`

You are already a fresh context, and you stay a leaf. Look up the plan you are
shipping. On a `HIT`, return the saved report to your Verify step. On a `MISS`,
read [the iwe-verifier rulebook](../../agents/iwe-verifier.agent.md) in full and
follow it in place, in its **In place inside `iwe-shipper`** mode, under the
plan key and the approvals your own prompt quotes — your verifier prompt; then
save its report and return it to your Verify step. Do not dispatch any agent.

## From a session

1. **Look up** the plan the user named, or `audit` in audit mode, with
   `--fresh` only when the request carries it. If neither a plan nor audit mode
   is clear from the request, ask the user first. On a `HIT`, re-post the saved
   report and stop.
2. **Build the dispatch prompt from the request alone.** It carries exactly:
   - **Plan key** — the plan the user named, as `data/plans/<YYYYMMDD>-<slug>`
     or its file path — or **audit mode** when the user asked for a
     workspace-wide drift check with no plan.
   - **Approvals** — each approval the user gave in this request, quoted
     verbatim, for example a command the verifier reported needing.

   Add nothing else: no summary of the conversation, no claim that tests pass
   or tasks are done, and never `--fresh`.

3. **Dispatch `iwe-verifier`** with that prompt, forwarding no conversation
   turns, and wait for its report.
4. **Save its report**, unless it reports `Needs decision`, with the user's
   request as the skill request and the step 2 prompt as the verifier prompt.
5. **Re-post its report verbatim.** When it reports `Needs decision`, name the
   approval or choice it needs and tell the user to re-run
   `/agentdev:iwe-verify <plan>` granting it.

## Rules

- Never perform a Verify step in this session from the session route — no
  check, no verification command. Every one belongs to the dispatched agent;
  the cache script's `lookup` and `save` are the only commands this session
  runs.
- Only `verify-cache.py` writes the saved report; never write or edit it by
  hand.
- Never paraphrase an approval into the prompt; quote it, or leave it out.
- Report-only: neither route fixes code, ticks a box, or mutates the graph.
