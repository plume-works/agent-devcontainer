---
type: someday
description: Give the ephemeral implementation document a name that says it tracks implementation progress for one story or bug, rather than "plan".
generated:
  by: claude-code/opus-5.5
  at: 2026-11-08T12:00:00Z
sources:
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-branch-name/SKILL.md
---

# Rename the plan document

Once plans are ephemeral (`architecture/ephemeral-plans`), a plan only tracks
implementation progress for one story or bug, and Ship deletes it. The name
"plan" then overlaps with what the story already settles.

A rename reaches the skill names (`/agentdev:iwe-plan`, `iwe-planner`),
`data/plans/`, the branch suffix `iter-<N>-plan` and
`/agentdev:iwe-branch-name`, and every spec that says "plan". The new name is
undecided.
