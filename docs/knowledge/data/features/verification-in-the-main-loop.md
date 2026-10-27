---
type: feature
stage: implemented
description: Ship invokes report-only Verify for every normal plan shipment and refuses all CRITICAL findings, while cancellation remains exempt.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-26T13:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-ship/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
---

# Verification in the main loop

## Purpose

The workspace skills form a loop — explore → plan → implement → ship — and
normal shipping invokes verification itself instead of relying on the user to
remember a separate pre-ship step.

Ship invokes Verify before spec synchronization or lifecycle transitions, so
requirement tracing, scenario coverage, and coherence checks are mandatory in
normal shipping.

## Behaviour

**Normal Ship invokes Verify.** Ship runs the report-only Verify workflow for
the selected plan and proceeds only when it reports zero CRITICAL findings. The
report lands in Ship's current context and is consumed immediately, so no
separate persisted verification artifact is required.

**Verify always runs from a fresh context.** Its rulebook is the `iwe-verifier`
catalog agent. `/agentdev:iwe-verify` dispatches it with a prompt carrying only
the plan key or audit mode and the user's quoted approvals, and re-posts its
report. Inside `iwe-shipper`, itself a fresh context, the Shipper follows the
same rulebook in place and still consumes the report in its own context. See
[Fresh-context Verify](../architecture/fresh-context-verify.md).

This keeps the loop at four steps, makes verification non-optional, and makes
the refusal mechanical rather than advisory.

Properties that should hold:

- Shipping a plan with any CRITICAL is refused, with no user override.
- Verify stays independently invocable — mid-implementation, or in audit mode —
  without shipping anything.
- Verify keeps writing nothing to the graph. Its report is consumed by ship in
  the same turn; "Report, never fix" is unaffected.
- The Implement orchestrator dispatches `iwe-verifier` after the plan's tasks
  close and acts on its findings ([Autonomous Implement
  loop](autonomous-implement-loop.md)). Ship stays the mandatory gate before any
  shipping state change.

**The coupling only bites for defects Verify can name.** Making Ship refuse a
CRITICAL raises the cost of a finding; it does not widen what counts as one. A
defect Verify has no rule for passes straight through the gate, and the
mandatory invocation makes that silence look like assurance.

Verify only blocks defects covered by its rules. Unsupported ticked tasks
produce a CRITICAL through [Make plan checkboxes carry their
evidence](../plans/20260815-honest-plan-checkboxes.md). The general lesson holds
for the next defect class: this feature is a transmission, not a detector.

## Edge cases

- **Cancelled plans use a separate path.** Explicit cancellation bypasses
  implementation verification, spec synchronization, feature or bug completion,
  and release recording. It updates the plan's cancelled state, validates, and
  commits.
- **Audit mode has no plan.** Verify's audit mode sweeps the whole graph and is
  not tied to a plan or a ship, so the coupling must leave that entry point
  reachable on its own.
- **Verify's own commands can have side effects.** Verify runs the plan's
  `## Verification` commands; one with effects beyond the working tree runs only
  under a quoted approval that names it, and otherwise Verify stops and reports
  the command. Invoking it from ship carries only the approvals Ship's own
  prompt quotes, never a blanket approval.
- **A plan with a thin `## Verification` section.** Ship would still pay the
  requirement-tracing and coherence passes for a plan whose verification is
  three green commands. Acceptable, but it is the main cost of the change.

## Open questions

None — every design question this feature raised is settled.

## Resolved decisions

- Mandatory verification lives in normal Ship. Verify remains available
  independently, and the Implement orchestrator dispatches `iwe-verifier` after
  the tasks; Ship stays the mandatory gate before any shipping state change.
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
