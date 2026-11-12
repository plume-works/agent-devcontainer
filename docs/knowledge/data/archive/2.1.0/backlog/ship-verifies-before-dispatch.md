---
type: task
stage: done
completed: 2026-11-03
priority: high
created: 2026-11-03
description: Run Verify from the iwe-ship skill as its own fresh subagent and have iwe-shipper only read the saved Verify report, so no Verify run ever lands in the Shipper's context.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-ship/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/agent-code/verify-cache.py
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: https://github.com/plume-works/agent-devcontainer/pull/657
---

# Run Verify from the iwe-ship skill, not inside the Shipper

## Problem

`iwe-shipper` is a dispatched subagent and cannot dispatch another, so when
Verify's saved report misses, it follows the `iwe-verifier` rulebook in its own
context (`iwe-verify` SKILL.md, "From inside `iwe-shipper`"). The whole Verify
run then sits in the Shipper's context ahead of the steps that mutate the graph.
On #657 the Shipper skipped step 6's bullet that writes the listed bug's
`## Fix`, and its step 7 re-check missed the gap.

## Today

```
session ── /iwe-ship ── dispatch ──► iwe-shipper   (fresh vs. your session)
                                        │
                                        ├─ step 3: Verify
                                        │    cache HIT  → read saved report
                                        │    cache MISS → run verifier rulebook in place (same context)
                                        ├─ step 4–5: spec merge
                                        ├─ step 6: stage flips + write ## Fix   ← skipped
                                        └─ step 7: re-inspect, commit
```

## Proposed

```
session ── /iwe-ship
              │
              ├─ verify-cache.py lookup <plan>
              │     HIT  → skip dispatch
              │     MISS → dispatch ──► iwe-verifier (fresh subagent)
              │                            └─ report ──► verify-cache.py save <plan> --commit <HEAD>
              │
              ├─ verdict has CRITICAL? → relay Ship blocker, stop (no Shipper dispatch)
              │
              └─ dispatch ──► iwe-shipper (fresh subagent)
                                 ├─ step 3: verify-cache.py lookup <plan>
                                 │     HIT  → use the saved report
                                 │     MISS → Ship blocker: no saved Verify report for HEAD
                                 │            (never runs Verify in place)
                                 ├─ step 4–5: spec merge
                                 ├─ step 6: stage flips + write ## Fix
                                 └─ step 7: re-inspect, commit
```

## Intent

- The `iwe-ship` skill runs the Verify step through the saved report: lookup,
  then on a miss a dispatched `iwe-verifier`, then save. This is the session
  route `/agentdev:iwe-verify` already takes.
- The Shipper only consumes Verify's result: its step 3 reads the saved report
  for its commit and catalog digest. A miss is a Ship blocker, never an in-place
  Verify run.
- The skill dispatches the Shipper on the same clean commit the report was saved
  for. If HEAD moved or the worktree is dirty, the Shipper's lookup misses and
  it returns a blocker.

## Open questions

1. `iwe-ship-all` and `iwe-plan` revise (answering a Ship blocker) also dispatch
   `iwe-shipper`. Do they get the same Verify-first step, or a shared route? If
   `iwe-ship-all` is itself a subagent, it cannot dispatch the verifier.
2. `iwe-verify`'s "From inside `iwe-shipper`" route and the verifier rulebook's
   "In place inside `iwe-shipper`" mode go away or become lookup-only.
3. On a CRITICAL verdict, should the skill stop before dispatching the Shipper,
   or dispatch it so the Shipper writes the blocker report?
4. Which `spec/` documents state Ship's Verify gate and need a delta.

## Why it matters

Less context in the Shipper means less attention spent before the graph
mutations, which is where #657's skipped `## Fix` happened. Verify keeps a fresh
context in every route instead of only the session route.
