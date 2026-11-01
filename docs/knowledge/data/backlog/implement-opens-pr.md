---
type: task
created: 2026-11-01
stage: planned
priority: medium
description: Add a standing AGENTS.md rule that authorizes an iwe-implement run to open or update its branch's pull request through pr-open, without asking, once it stops with committed work.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T01:52:51Z
sources:
- resource: AGENTS.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
---

# Let iwe-implement open its pull request without asking

The agent harness forbids opening a pull request unless the user asks for one,
so an `/agentdev:iwe-implement` run that stops with committed work — at a plan
gate, a blocker, or the end of its tasks — has to ask before every
`/agentdev:pr-open`. A rule in the repository's `AGENTS.md` is a durable
authorization that lifts that default for this one workflow.

## Scope

- One rule in `AGENTS.md`: when an `/agentdev:iwe-implement` run reaches a
  stopping point with committed work on a plan work branch, it opens or updates
  that branch's pull request through `/agentdev:pr-open` without asking.
- The rule covers the implement workflow only; any other pull request still
  needs the user's request.
- Merging stays a separate, user-requested step.
