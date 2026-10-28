---
type: task
created: 2026-10-27
stage: done
completed: 2026-10-27
priority: medium
description: Run /agentdev:iwe-implement-all live against two active fixture plans, so the e2e suite checks that the coordinator dispatches the implementer and runs the Verify loop once per plan rather than only for a single plan.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-27T14:20:00Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md
- resource: scripts/e2e/iwe-workflows/clone.py
- resource: scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py
- resource: scripts/e2e/iwe-workflows/test_iwe_workflows_codex.py
- resource: scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py
---

# Run implement-all live against two plans

`test_implement_all` runs `/agentdev:iwe-implement-all` on Claude Code, Codex,
and OpenCode against a fixture commit where the loop plan is the only active
plan. One plan cannot show the coordinator's per-plan behavior that
`iwe-implement-all/SKILL.md` specifies: one `iwe-implementer` dispatch per plan,
waiting for each report before the next, and `## Running the loop` (an
`iwe-verifier` dispatch) for each plan before the next dispatch.

The work: add a second plain fixture plan that writes its own file and has a
`Verification` check, keep it active next to the loop plan on the fixture commit
`implement_all` uses, and have each harness's `test_implement_all` assert two
implementer dispatches, one naming each plan; two verifier dispatches; no
evaluator; and both plans' tasks ticked with evidence and their files written.

It matters because the coordinator is what [Let Implement verify, fix, and
revise on its own](../plans/20261026-autonomous-implement-loop.md) left checked
only by Verify reading the skill text for more than one plan.

Dependency ordering stays out: the coordinator runs no Ship, so a plan that
depends on another active plan always stops at its own dependency check, and
covering that is a separate scenario.
