---
type: task
created: 2026-10-30
stage: planned
priority: medium
description: Add IWE workflow e2e scenarios that prove the Shipper reuses a saved Verify report without running verification commands, and that Verify stops on a dirty worktree before any dispatch.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T15:00:00Z
sources:
- resource: scripts/e2e/iwe-workflows/scenarios.py
- resource: scripts/e2e/iwe-workflows/test_iwe_workflows_claude.py
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
---

# Exercise the saved Verify report end to end

[Verify report cache](../features/verify-report-cache.md) tests its script in
`.agents/plugins/agentdev/tests/test_verify_cache.py`, but the routing that
reacts to the script's results lives in skill and agent prose, and the IWE
workflow e2e suite asserts only dispatch counts. Nothing proves that an agent
following the prose actually skips the work on a hit.

Add scenarios on Claude Code, Codex, and OpenCode for:

- **Ship after a saved report** — a clone where the Implement loop's Verify
  saved a `Ready to ship` report for `HEAD`: `/agentdev:iwe-ship` runs no
  `## Verification` command and its report names the saved report's commit.
- **Dirty worktree** — `/agentdev:iwe-verify` on a clone with an untracked file
  dispatches no `iwe-verifier` and reports the dirty paths.
- **Needs decision is not reused** — a re-run granting the approval after a
  `Needs decision` report dispatches the verifier again.
