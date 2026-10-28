---
name: iwe-planner
description: E2E stub that drafts the same narrowing revision of the revise fixture plan every time. Followed in place by the Implement orchestrator applying a revision; never dispatched and never started on a description match.
tools: Bash, Read, Edit, Write, Grep, Glob
---

# Draft the fixture's narrowing revision

This is a test stub standing in for the real planner rulebook. It runs in place
and is never dispatched.

## How you run

- **From the Implement orchestrator** — draft the revision by replacing the
  whole content of `docs/knowledge/data/plans/20261026-e2e-revise.md` with the
  content of `e2e/revise.narrowed.md`. Run `iwe normalize` and
  `iwe schema validate` from the repository root. Run no audit, commit
  nothing, and stop with the revision uncommitted for the
  `iwe-revision-evaluator`.
- **From `/agentdev:iwe-plan`** — stop and report that this checkout carries a
  test stub in place of the planner.
