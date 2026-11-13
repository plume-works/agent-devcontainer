---
type: bug
stage: pending
severity: medium
description: Two runs of the ASD-STE100 audit on the same text give different findings, and a run can report the replacement text that an earlier run gave.
sources:
- resource: .agents/plugins/agentdev/skills/audit-ste100/SKILL.md
- resource: .agents/plugins/agentdev/agents/ste100-auditor.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-plan-review/SKILL.md
- resource: https://github.com/plume-works/agent-devcontainer/pull/873
- resource: https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-simple-english
- resource: https://github.com/AminBlg/SimpleEnglish
---

# Bug: the ASD-STE100 audit gives different findings for the same text

## Symptom

`/agentdev:audit-ste100` does not give the same report two times for the same
text. One run reports a sentence, and the next run passes it. A run can also
report the replacement text that an earlier run gave. Thus a writer who applies
each replacement does not get to `No findings.` in a known number of rounds.

The `STE100 Auditor` agent and `/agentdev:iwe-plan-review` use this audit, so
the plan review has the same problem.

## Reproduction

1. Read the reviews of pull request #873. The AI reviewer requested changes
   three times. Each time, it reported the added prose against ASD-STE100. Some
   of the reported text was a replacement that its own earlier review gave.
2. Run the `STE100 Auditor` two times on one unchanged file in file scope.
   Compare the two tables. The rows are not the same.

## Root cause

The audit has no fixed rule set.
`.agents/plugins/agentdev/skills/audit-ste100/SKILL.md#the-source-of-the-rules`
tells the model to check "from your own knowledge of the standard". The skill
gives examples of rules, but no full list with rule numbers. Each run thus
decides again which rules apply and how. Nothing in the report ties a finding to
a fixed rule, so two runs cannot agree.

## Potential solution

Base the audit on the Simple English skill by AminBlg, under the MIT license.
Hermes Agent supplies a port of it as `optional-skills/creative/simple-english`.
That skill has these parts:

- a fixed catalog of 53 rules in nine sections, with a number for each rule,
  from ASD-STE100 Issue 9;
- a check mode that reports each break with its rule number, the text, and a
  replacement;
- a checklist reference for a full audit pass;
- a self-check that the model runs on its replacement before it reports.

A fixed rule catalog with rule numbers gives each run the same rules. The
self-check stops a replacement that breaks a rule.
