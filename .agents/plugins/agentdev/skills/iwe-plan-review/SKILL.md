---
name: iwe-plan-review
description: Review one IWE plan draft from three fresh contexts at once — the Durable Knowledge Auditor for durable-knowledge residue, iwe-plan-reviewer for the plan rules, and iwe-ship-reviewer in plan mode for what Ship will need — and return the reports unchanged; report-only. Use when the iwe-planner rulebook reaches its review step on a created or revised plan, in every mode. Conformance of code to a plan belongs to /agentdev:iwe-verify, and attacking a plan's design to /agentdev:iwe-adversarial-review.
---

# Review a plan draft

Every plan edit is read cold by three reviewers before it is validated: the
`Durable Knowledge Auditor` agent audits it for durable-knowledge residue,
`iwe-plan-reviewer` checks it against [the plan rules](references/plan-rules.md),
and `iwe-ship-reviewer` in plan mode checks it gives Ship what it needs. This
skill runs all three and hands their reports back to the caller, which applies
them.

## Steps

1. **Resolve the plan.** The request names one plan —
   `data/plans/<YYYYMMDD>-<slug>`, its file path, or its slug. Resolve it to
   both the plan file path and the plan key. If it names none, or matches more
   than one plan, stop and say which.
2. **Dispatch the three agents in parallel**, in one message, forwarding no
   conversation turns. Each prompt carries exactly this and nothing else:
   - `Durable Knowledge Auditor` — the plan file path and the scope `plan`.
   - `iwe-plan-reviewer` — the plan key and the absolute path of
     `references/plan-rules.md` in this skill's directory.
   - `iwe-ship-reviewer` — the plan key and the mode `plan`.
3. **Wait for the three reports**, then re-post each verbatim in your final
   message text under its agent's name: a subagent's result is tool output the
   user may never see.

## Rules

- Perform no review step in this session — every check belongs to a dispatched
  agent.
- Add nothing to any prompt: no summary of the draft, no claim that it is
  sound, no note of what changed, no rule quoted from the plan rules.
- Report-only: this skill edits no file and commits nothing. Applying the
  verdicts and resolving the findings belongs to the caller.
