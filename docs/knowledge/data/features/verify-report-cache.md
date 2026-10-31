---
type: feature
stage: implemented
description: Verify saves its last report per plan, keyed by the commit it ran on and the active catalog digest, and returns that report instead of re-running when invoked again on the same clean commit, so Ship reuses the Implement loop's Verify instead of repeating its test and e2e runs.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T03:33:48Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
---

# Verify report cache

## Purpose

The regular flow is Implement → Verify → Ship → `pr-open` on one branch. The
Implement loop's last Verify and the Shipper's Verify judge the same commit, and
each re-runs the plan's `## Verification` commands — full test suites and e2e
runs. The second run adds no information: the first already came from a fresh
context. Caching the report in the Verify skill gives every caller the saved
verdict for a commit it has already judged.

## Behaviour

- `/agentdev:iwe-verify` refuses to run on a dirty worktree: any tracked change
  or untracked file Git does not ignore.
- Each run that ends in `Ready to ship`, `Blocked`, or `Audit` overwrites one
  saved report per plan (one for audit mode), whose frontmatter records the
  commit it ran on and the digest of the active agentdev catalog.
- A later invocation on the same commit with the same catalog digest returns the
  saved report, marked as saved, without running any check or verification
  command.
- The saved report's frontmatter records the request the skill was invoked with
  and the prompt the verifier ran under, including the approvals it quotes, so a
  reused verdict shows what it was granted.
- A `Needs decision` report is never saved, so re-running with the approval runs
  Verify.
- `--fresh`, given by the user, runs Verify and overwrites the saved report.
- The Shipper's Verify step and the Implement loop both go through the skill, so
  both read and write the same saved report.

## Edge cases

- A verification command that leaves the worktree dirty is a Verify CRITICAL,
  since the saved report would no longer describe a clean commit.
- A new commit, a rebase, or an updated catalog changes the key, so the next
  invocation runs Verify in full.
- A fresh container has no saved report and runs Verify in full.

## Open questions

None — re-checking incrementally from a saved report on an ancestor commit is
tracked separately in [Re-verify incrementally from a saved
report](../backlog/incremental-re-verify.md).
