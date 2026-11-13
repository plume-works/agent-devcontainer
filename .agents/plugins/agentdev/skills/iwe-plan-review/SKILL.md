---
name: iwe-plan-review
description: Review one IWE plan draft from fresh contexts. The STE100 Auditor checks the prose rule first and alone. When it finds no break, the Durable Knowledge Auditor checks for durable-knowledge residue, iwe-plan-reviewer checks the plan rules, and iwe-ship-reviewer in plan mode checks what Ship needs. The skill returns the reports unchanged and only reports. Use when the iwe-planner rulebook reaches its review step on a created or revised plan, in every mode. Conformance of code to a plan belongs to /agentdev:iwe-verify, and attacking a plan's design to /agentdev:iwe-adversarial-review.
---

# Review a plan draft

Fresh contexts read each plan edit before validation. The `STE100 Auditor`
agent reads it first and checks the prose against ASD-STE100 Issue 9. When that
agent finds no break, three agents read the draft at the same time:

- The `Durable Knowledge Auditor` agent checks it for durable-knowledge residue.
- `iwe-plan-reviewer` checks it against [the plan rules](references/plan-rules.md).
- `iwe-ship-reviewer` in plan mode checks that it gives Ship what Ship needs.

This skill runs the agents and gives their reports to the caller. The caller
applies them.

## Steps

1. **Resolve the plan.** The request names one plan —
   `data/plans/<YYYYMMDD>-<slug>`, its file path, or its slug. Resolve it to
   both the plan file path and the plan key. If it names none, or matches more
   than one plan, stop and say which.
2. **Dispatch the `STE100 Auditor` alone.** Dispatch no other agent before
   it or with it. Send no conversation turns. The prompt holds only the plan
   file path and the scope `plan`. Wait for its report.
3. **Stop on a finding.** When the report has a finding, write the report in
   your last message, with no change, under the name `STE100 Auditor`.
   Dispatch no other agent. The caller corrects the draft and runs this skill
   again.
4. **Dispatch the three other agents at the same time**, in one message, when
   the report has no finding. Send no conversation turns. Each prompt holds
   only this text:
   - `Durable Knowledge Auditor` — the plan file path and the scope `plan`.
   - `iwe-plan-reviewer` — the plan key and the absolute path of
     `references/plan-rules.md` in this skill's directory.
   - `iwe-ship-reviewer` — the plan key and the mode `plan`.
5. **Wait for the three reports.** Then write the four reports in your last
   message, each with no change and under the name of its agent. The user
   possibly does not see the result of a subagent, because it is tool output.

## Rules

- Perform no review step in this session — every check belongs to a dispatched
  agent.
- Add nothing to any prompt: no summary of the draft, no claim that it is
  sound, no note of what changed, no rule quoted from the plan rules.
- Report-only: this skill edits no file and commits nothing. Applying the
  verdicts and resolving the findings belongs to the caller.
