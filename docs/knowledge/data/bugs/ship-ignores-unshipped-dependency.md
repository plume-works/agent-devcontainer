---
type: bug
description: iwe-shipper never checks a plan's `## Depends on`, so Ship and the ship-all coordinator can ship a plan whose prerequisite is still active — including one that came back Blocked earlier in the same ship-all run.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T15:55:00Z
sources:
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-ship-all/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md
---

# Bug: Ship ships a plan whose prerequisite has not shipped

## Symptom

`/agentdev:iwe-ship-all` dispatches `iwe-shipper` once per plan in dependency
order, but a plan whose prerequisite came back `Blocked` or `Needs decision`
earlier in the run is still dispatched, and with a clean Verify it ships to
`stage: done` while its prerequisite stays active. `/agentdev:iwe-ship` on a
single plan has the same gap. The graph then records a plan as shipped on top of
behavior that has not shipped.

## Reproduction

The rulebooks define this outcome; it follows from the steps below without a
live run.

1. Two active plans, A and B, with every task ticked and B's `## Depends on`
   linking A.
2. A has a Verify CRITICAL; B verifies clean.
3. Run `/agentdev:iwe-ship-all`. The coordinator ships A first: the Shipper
   returns `Blocked` and A stays under `## Active`.
4. The coordinator then dispatches the Shipper for B. Neither the coordinator
   nor the Shipper consults B's `## Depends on`, so B ships: `stage: done`, its
   link moved to `## Done`, specs merged.

## Root cause

The dependency check exists only on the Implement side.
`iwe-implementer.agent.md` step 3 stops when any prerequisite lacks
`stage: done`, and `iwe-implement-all` relies on that check ("stops at its own
dependency check"). `iwe-shipper.agent.md` has no equivalent step in its normal
shipping path, and `iwe-ship-all` only orders dispatches by `## Depends on`; it
does not act on a prerequisite's outcome.

## Fix

Unfixed. Direction: a `## Depends on` check in the Shipper's normal-shipping
path — every prerequisite plan must carry `stage: done`, otherwise a Ship
blocker report naming the unshipped prerequisite, before Verify and with no
mutation. That mirrors the implementer's check and covers both `iwe-ship` and
`iwe-ship-all`.

## Key references

Verified anchor points (line numbers as of 2026-10-31):

- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:49` — step 1, select the
  operation and inspect current state (no dependency check)
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md:71` — step 3, Run Verify
  for normal shipping
- `.agents/plugins/agentdev/skills/iwe-ship-all/SKILL.md:13` — dispatch once per
  plan in dependency order
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:45` — step 3, Check
  `## Depends on`
- `.agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md:16` — relies on
  the implementer's dependency check
