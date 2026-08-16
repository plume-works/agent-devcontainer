---
type: feature
stage: implemented
description: Ship invokes report-only Verify for every normal plan shipment and refuses all CRITICAL findings, while cancellation remains exempt.
generated:
  by: claude-code/opus-5
  at: 2026-08-16T00:00:00Z
sources:
- .claude/skills/verify/SKILL.md
- .claude/skills/ship/SKILL.md
---

# Verification in the main loop

## Purpose

The workspace skills form a loop — explore → plan → implement → ship — and
normal shipping now invokes verification itself instead of relying on the user
to remember a separate pre-ship step.

Previously, Ship asked for a loose confirmation of the plan's `## Verification`
section and described Verify as only the thorough form of that step. That
allowed normal shipping without requirement tracing, scenario coverage, or
coherence checks against `## Approach` and `## Out of scope`.

Ship now closes that gap by consuming a Verify report in the same invocation,
before it synchronizes specs or changes durable lifecycle state.

## Behaviour

**Normal Ship invokes Verify.** Ship runs the report-only Verify workflow for
the selected plan and proceeds only when it reports zero CRITICAL findings. The
report lands in Ship's current context and is consumed immediately, so no
separate persisted verification artifact is required.

This keeps the loop at four steps, makes verification non-optional, and makes
the refusal mechanical rather than advisory.

Properties that should hold:

- Shipping a plan with any CRITICAL is refused, with no user override.
- Verify stays independently invocable — mid-implementation, or in audit mode —
  without shipping anything.
- Verify keeps writing nothing to the graph. Its report is consumed by ship in
  the same turn; "Report, never fix" is unaffected.
- Implement continues to run task evidence and final plan commands, but does not
  automatically invoke the full Verify workflow. Ship is the one mandatory
  integration point.

**The coupling only bites for defects Verify can name.** Making Ship refuse a
CRITICAL raises the cost of a finding; it does not widen what counts as one. A
defect Verify has no rule for passes straight through the gate, and the
mandatory invocation makes that silence look like assurance.

Ticked-box over-claiming was exactly that blind spot. Verify audited unchecked
boxes and took ticked ones on faith, so a plan whose boxes were all flipped in
one careless edit produced a clean report — the loop's strongest gate had
nothing to say about its most load-bearing claim. Verify gained the ticked-box
counterpart in
[Make plan checkboxes carry their evidence](../plans/20260815-honest-plan-checkboxes.md);
before that, this feature would have inherited the gap rather than closed it.
The general lesson holds for the next defect class: this feature is a
transmission, not a detector.

## Edge cases

- **Cancelled plans use a separate path.** Explicit cancellation bypasses
  implementation verification, spec synchronization, feature or bug completion,
  and release recording. It updates the plan's cancelled state, validates, and
  commits.
- **Audit mode has no plan.** Verify's audit mode sweeps the whole graph and is
  not tied to a plan or a ship, so the coupling must leave that entry point
  reachable on its own.
- **Verify's own commands can have side effects.** Verify runs the plan's
  `## Verification` commands; it currently requires the user's go-ahead for
  anything with effects beyond the working tree. Invoking it automatically from
  ship must preserve that prompt rather than inheriting a blanket approval.
- **A plan with a thin `## Verification` section.** Ship would still pay the
  requirement-tracing and coherence passes for a plan whose verification is
  three green commands. Acceptable, but it is the main cost of the change.

## Resolved decisions

- Mandatory verification lives in normal Ship only. Verify remains available
  independently, and Implement does not gain a second automatic invocation.
- A CRITICAL finding is not overridable. Three outcomes remain: the plan stays
  active for fixes, it can be revised to drop the offending work (via the plan
  skill's revise mode, which treats that as a material scope change and asks the
  user first), or it can be explicitly cancelled. Known-false durable claims are
  never shipped. Revision is the proportionate route when the user has decided
  against a single task: it cannot be ticked while undone, and cancelling the
  whole plan over it is out of scale.
- Explicit cancellation is exempt because it records abandonment rather than
  implemented behavior and performs no release or implemented-feature
  transition.
