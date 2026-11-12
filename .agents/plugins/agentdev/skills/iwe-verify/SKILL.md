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
commit Verify already judged gets that verdict back without a second run. Every
caller — the user's session, the Implement loop, and `iwe-shipper` — takes the
same route, which starts and ends at the cache.

## The saved report

[verify-cache.py](agent-code/verify-cache.py) keeps one saved report per plan,
and one for audit mode, keyed by the commit Verify ran on and the digest of the
active agentdev catalog. Run it from the repository root. Its target is the plan
key, or `audit` in audit mode.

**Returning the report** means putting its body, verbatim, into your final
message text. A path to the saved report does not count, and neither does the
report appearing only inside a tool call or a tool result, such as a `Read`
result or the save heredoc.

**Look up** before any Verify step, adding `--fresh` only when the user's own
request carries it:

```bash
agent-code/verify-cache.py lookup <plan-key|audit> [--fresh]
```

| RESULT            | Exit   | Action                                                                                                                                                |
| ----------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `HIT`             | `3`    | Read the file `REPORT` names and return its body verbatim in your final message text, led by `Saved Verify report from <COMMIT>`. Run no Verify step. |
| `MISS`            | `4`    | Run Verify by the route below, keeping `COMMIT` for the save.                                                                                         |
| `DIRTY_WORKTREE`  | `5`    | **STOP.** Report that Verify runs only on a clean worktree, with the paths stderr lists. Commit or remove them, then run Verify again.                |
| `PREFLIGHT_ERROR` | `2`    | **STOP.** Report the blocker verbatim (not a repository, no commit, bad arguments).                                                                   |
| `SCRIPT_FAILURE`  | `1`    | **STOP.** Report the blocker verbatim; do not retry or work around it.                                                                                |
| `SIGNAL_*`        | `129`+ | **STOP.** The run was interrupted; report it.                                                                                                         |

**Save** the report the run produced, verbatim on stdin, with the `COMMIT` the
miss printed, the verdict its lead line names — `Ready to ship`, `Blocked`, or
`Audit` — and two prompts, each verbatim, which the saved report records but
does not key on:

- **Skill request** — the request this skill was invoked with: the user's
  words, or the plan key and approvals the Implement loop or the Shipper
  invoked it with.
- **Verifier prompt** — the dispatch prompt `iwe-verifier` ran under.

Never save a `Needs decision` report. Single-quote each prompt, newlines
included, and write a single quote inside one as `'\''`; the report goes on
stdin through a quoted heredoc:

```bash
agent-code/verify-cache.py save <plan-key|audit> --commit <COMMIT> \
  --verdict '<verdict>' \
  --skill-request '<the skill request, verbatim>' \
  --verifier-prompt '<the verifier prompt, verbatim>' <<'VERIFY_REPORT'
<the report, verbatim>
VERIFY_REPORT
```

| RESULT            | Exit   | Action                                                                                                                                                   |
| ----------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SUCCESS`         | `0`    | Return the report verbatim in your final message text.                                                                                                   |
| `DIRTY_WORKTREE`  | `5`    | Return the report unsaved, verbatim in your final message text, and say the worktree was dirty after the run, so the next Verify will not reuse it.      |
| `HEAD_MOVED`      | `6`    | Return the report unsaved, verbatim in your final message text, and say `HEAD` moved off `COMMIT` during the run, so the report may not describe `HEAD`. |
| `PREFLIGHT_ERROR` | `2`    | Return the report unsaved, verbatim in your final message text, with the error verbatim.                                                                 |
| `SCRIPT_FAILURE`  | `1`    | Return the report unsaved, verbatim in your final message text, with the error verbatim.                                                                 |
| `SIGNAL_*`        | `129`+ | Return the report unsaved, verbatim in your final message text, and say the save was interrupted.                                                        |

## From a session

Inside `iwe-shipper`, the request is the plan you are shipping and the
approvals your own prompt quotes, and your final message text is the Shipper's
report, which carries the Verify report.

1. **Look up** the plan the user named, or `audit` in audit mode, with
   `--fresh` only when the request carries it. If neither a plan nor audit mode
   is clear from the request, ask the user first. On a `HIT`, re-post the saved
   report verbatim in your final message text, led by
   `Saved Verify report from <COMMIT>`, and stop. The saved report's path, or
   the `Read` result that showed it, does not count as re-posting it.
2. **Build the dispatch prompt from the request alone.** It carries exactly:
   - **Plan key** — the plan the user named, as `data/plans/<YYYYMMDD>-<slug>`
     or its file path — or **audit mode** when the user asked for a
     workspace-wide drift check with no plan.
   - **Approvals** — each approval the user gave in this request, quoted
     verbatim, for example a command the verifier reported needing. Inside
     `iwe-shipper`, these are the approvals your own prompt quotes.

   Add nothing else: no summary of the conversation, no claim that tests pass
   or tasks are done, and never `--fresh`.

3. **Dispatch `iwe-verifier`** with that prompt, forwarding no conversation
   turns, and wait for its report.
4. **Save its report**, unless it reports `Needs decision`, with the user's
   request as the skill request and the step 2 prompt as the verifier prompt.
5. **Re-post its report verbatim** in your final message text: the subagent's
   result and the save heredoc are tool output the user may never see, and a
   path to the saved report does not count. When it reports `Needs decision`,
   name the approval or choice it needs and tell the user to re-run
   `/agentdev:iwe-verify <plan>` granting it.

## Rules

- Never perform a Verify step in this session — no check, no verification
  command. Every one belongs to the dispatched agent;
  the cache script's `lookup` and `save` are the only commands this session
  runs.
- Only `verify-cache.py` writes the saved report; never write or edit it by
  hand.
- Never paraphrase an approval into the prompt; quote it, or leave it out.
- Report-only: this skill fixes no code, ticks no box, and mutates no graph.
