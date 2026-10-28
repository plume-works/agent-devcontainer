---
type: task
created: 2026-10-28
stage: planned
priority: medium
description: Explore a way for plan task evidence to stay traceable after rebases and squash merges, since evidence lines name commits whose ids those operations rewrite or erase.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-28T10:45:00Z
sources:
- resource: docs/knowledge/data/spec/plan-checkbox-evidence.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
---

# Make plan task evidence survive history rewrites

[Plan checkbox evidence](../spec/plan-checkbox-evidence.md) makes a ticked
task's evidence name the commit that holds its change, and Verify, and the Ship
run that repeats it, check that the commit can be traced. Commit ids do not
last:

- **Rebase** gives every rebased commit a new id. [Stacked
  PRs](../architecture/stacked-prs.md) rebase every layer above a change, so
  evidence written on a lower layer goes stale before the stack merges.
- **Squash merge** replaces a PR's commits with one commit on the default
  branch. Once the branch is deleted, every evidence line in the PR's plans
  points at a commit that no longer exists anywhere a later session can reach.
- **Amend** changes the id the moment it runs, so evidence cannot name the
  commit it is written in.

A commit subject survives a rebase but not a squash. So today a shipped plan's
evidence is checkable only until its PR merges, and a long-lived stack's
evidence only until its next rebase.

The work is to explore and decide how evidence is named so a later session can
still look it up, then record the decision in `data/architecture/` and change
the spec through a plan. Leads to weigh:

- The codebase map's `source_digest` already solved the same problem for map
  docs: it fingerprints tracked content rather than naming a commit, so it stays
  valid across squash merges and branch rewrites.
- The PR number survives both rebase and squash and links the squashed commit to
  the branch's history.
- A path plus a test name, re-runnable from any tree that holds the change.

Closing it can also be the decision that the current rule is good enough for one
PR's lifetime, recorded with its reason.
