---
type: task
created: 2026-10-30
stage: planned
priority: medium
description: Let a Verify run whose HEAD descends from a commit with a saved Verify report re-check only what changed since that commit, instead of re-running every check and verification command.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T12:00:00Z
sources:
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
rank: 1900
---

# Re-verify incrementally from a saved report

Builds on Verify report caching, which saves each Verify report keyed by plan
key and the commit it ran on, and returns the saved report when Verify runs
again on that same commit. That caching saves nothing once a commit lands, so
every Implement loop round after a fix re-runs every check and every
`## Verification` command — full test suites and e2e runs — even when the fix
was a one-line evidence edit.

The work: when no report exists for `HEAD` but one exists for a commit that is
an ancestor of `HEAD`, re-check only what the diff since that commit can affect,
and carry the rest of the earlier verdict forward. Settling it means deciding:

- how a check or verification command declares the paths its result depends on,
  and what happens to a command that declares none;
- which findings an earlier report may carry forward, and which a diff always
  re-opens;
- how the new report shows which parts it re-checked and which it carried
  forward, so its verdict is not read as a full run.

A rebase or squash rewrites the ancestor commit, which ends reuse; the same
limit is tracked for evidence lines in [Make plan task evidence survive history
rewrites](resilient-task-evidence.md).
