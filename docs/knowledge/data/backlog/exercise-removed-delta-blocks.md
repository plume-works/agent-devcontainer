---
type: task
created: 2026-08-16
stage: pending
priority: medium
description: Exercise the REMOVED Requirements delta operation end to end, which the risk-scaled spec-delta work specified but never ran against a real retirement.
sources:
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-ship/SKILL.md
- resource: docs/knowledge/data/plans/20260816-structured-plan-spec-deltas.md
rank: 1800
---

# Exercise REMOVED delta blocks end to end

[Embed structured spec deltas in IWE
plans](../archive/1.0.0/plans/20260816-structured-plan-spec-deltas.md) specified
three delta operations and worked two of them. `ADDED` and `MODIFIED` were
written, verified, and merged into IWE workflow skills by that plan's own
`## Spec changes`. For this reason, a real merge supports the contract for those
two. The same pass specified `REMOVED`, but nothing ran it. No plan in this
workspace removed a requirement, so nobody wrote, verified, or merged a
`## REMOVED Requirements` block.

The plan's `## Verification` asked for more than was delivered — it names a
contract-heavy fixture carrying complete `ADDED`, `MODIFIED`, **and** `REMOVED`
blocks. Verify recorded this as a WARNING at ship time rather than a CRITICAL,
because no ticked task claimed otherwise; the gap is in verification coverage,
not in a false evidence line. Shipping proceeded on that basis.

## What to do

Wait for the first plan that genuinely retires a requirement and use it as the
fixture, rather than inventing a retirement to exercise the path. When it comes:

- Author the `## REMOVED Requirements` block with the retirement reason that
  `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md` requires.
- Confirm Verify treats a removal that drops a still-live scenario as a
  CRITICAL, and that a legitimate retirement passes.
- Confirm Ship's second pass accounts for the `REMOVED` operation and that the
  durable spec loses exactly the retired requirement, with unaffected content
  surviving untouched.
- Check the requirement-level `REMOVED` path stays distinct from whole-spec
  retirement via `iwe delete`.

If no such plan appears within a few cycles, the honest alternative is to narrow
the plan's verification claim to the two operations actually exercised, rather
than leaving an unmet bullet standing in a shipped plan.

## Why it is not urgent

The operation is fully specified and carried by all four skills — Plan
`.agents/plugins/agentdev/skills/iwe-plan/SKILL.md`, Implement
`.agents/plugins/agentdev/skills/iwe-plan/SKILL.md`, Verify
`.agents/plugins/agentdev/skills/iwe-plan/SKILL.md`, Ship
`.agents/plugins/agentdev/skills/iwe-plan/SKILL.md` and
`.agents/plugins/agentdev/skills/iwe-plan/SKILL.md`. Nothing is missing from the
contract; what is missing is a worked instance proving the four agree in
practice. The risk is that the three operations were written together and only
two were ever pressure-tested, so a disagreement about `REMOVED` would first
surface during a real retirement.
