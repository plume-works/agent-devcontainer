---
type: feature
stage: implemented
description: A fresh-context reviewer checks every plan against what Ship will need, and every shipped plan against what Ship had to do, stamping the shipped plan with a fixed Ship review checklist.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-ship/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: https://github.com/plume-works/agent-devcontainer/pull/657
---

# Ship review

## Purpose

`iwe-shipper` checks its own work before it commits, and that check can miss a
step it skipped: on pull request #657 it set a bug to `stage: done` without the
`## Fix` section Ship requires. A reviewer from a fresh context catches what the
Shipper's own re-check misses, and a plan that would not give Ship what it needs
is caught before it is implemented.

## Behaviour

- The catalog agent `iwe-ship-reviewer` checks Ship's obligations, as the steps
  of `iwe-shipper.agent.md` define them, in one of two modes.
- **Plan mode**, run by `/agentdev:iwe-plan-review` on every plan edit, reports
  whether the plan gives Ship what it needs and changes nothing.
- **Ship mode**, run by `/agentdev:iwe-ship` after `iwe-shipper` commits, checks
  the shipped plan. When every obligation holds, it appends a `## Ship review`
  section to the plan: a fixed checklist, every item ticked `confirmed` or `N/A`
  with a reason. When one does not, `/agentdev:iwe-ship` re-dispatches
  `iwe-shipper` with only the gaps to fix, without re-running Verify, up to 3
  times.

## Edge cases

- The Verify, plan-stage, and hub-edit items always apply and are never `N/A`.
- After 3 fix rounds with a gap left, `/agentdev:iwe-ship` reports the gap and
  the plan stays without a `## Ship review`.
- Plans shipped before the reviewer existed get a backfilled `## Ship review`.

## Open questions

None open.
