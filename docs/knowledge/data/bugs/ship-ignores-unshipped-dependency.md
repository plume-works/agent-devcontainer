---
type: bug
stage: planned
severity: high
description: iwe-shipper never checks a plan's `## Depends on`, so /agentdev:iwe-ship can ship a plan whose prerequisite is still active, including one Ship returned Blocked.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-08T05:10:00Z
sources:
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
rank: 550
---

# Bug: Ship ships a plan whose prerequisite has not shipped

## Symptom

`/agentdev:iwe-ship` on a plan whose `## Depends on` links a plan that is still
active ships it anyway: with a clean Verify it reaches `stage: done` while its
prerequisite stays active, including a prerequisite Ship returned `Blocked` or
`Needs decision` for. The graph then records a plan as shipped on top of
behavior that has not shipped.

## Reproduction

The rulebooks define this outcome; it follows from the steps below without a
live run.

1. Two active plans, A and B, with every task ticked and B's `## Depends on`
   linking A.
2. A has a Verify CRITICAL; B verifies clean.
3. Run `/agentdev:iwe-ship` on A. The Shipper returns `Blocked`, and A stays
   active.
4. Run `/agentdev:iwe-ship` on B. The Shipper never consults B's
   `## Depends on`, so B ships: `stage: done`, specs merged.

## Root cause

The dependency check exists only on the Implement side.
`iwe-implementer.agent.md` step 3 stops when any prerequisite lacks
`stage: done`. `iwe-shipper.agent.md` has no equivalent step in its normal
shipping path.

## Potential solution

A `## Depends on` check in the Shipper's normal-shipping path — every
prerequisite plan must carry `stage: done`, otherwise a Ship blocker report
naming the unshipped prerequisite, before Verify and with no mutation. That
mirrors the implementer's check.

## Key references

Verified anchor points (line numbers as of 2026-11-08):

- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:49` — step 1, select the
  operation and inspect current state (no dependency check)
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:71` — step 3, Run Verify
  for normal shipping
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:44` — step 3, Check
  `## Depends on`
