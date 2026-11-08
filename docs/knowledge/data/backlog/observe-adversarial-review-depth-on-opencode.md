---
type: task
created: 2026-11-05
stage: pending
priority: low
description: Rerun the plan-target adversarial review on OpenCode after the reviewer was told to check every rubric part and report every finding, and record whether OpenCode models now find the structural weaknesses Claude Code finds.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-adversarial-reviewer.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-adversarial-review/SKILL.md
---

# Check adversarial review depth on OpenCode

On the same fixture plan, `/agentdev:iwe-adversarial-review <plan> plan`
reported five weaknesses on Claude Code and one or two on every OpenCode model
tried (`openai/gpt-6.1-sol` at default and high effort, `gpt-6-astra`,
`gpt-6-astra-fast`). No OpenCode run reported the two structural weaknesses:
that no code calls the mechanism the plan's requirement relies on, and that an
input the plan itself produces — a full plan key — always fails the check. Those
are the findings that would change a plan most.

The `iwe-adversarial-reviewer` rules now tell the reviewer to check every part
of the rubric for the target, including a mechanism no caller reaches and a
scenario no task covers, and to report every finding, not only the most severe.

Rerun the plan-target review on OpenCode with `openai/gpt-6.1-sol` at default
effort against a fixture plan that has both a path-handling hole and an uncalled
mechanism. Done when the run is recorded with the weaknesses it reported: either
it now reports a structural weakness, or the gap stands and the decision on it —
a sharper rubric, a different default model, or accepting the gap — is recorded.

Priority is low because the review already finds a real weakness on every model
tried.
