---
type: feature
stage: proposed
status: draft
description: Make ship invoke verify and refuse on CRITICAL, so verification is a step the loop performs rather than one the user must remember.
generated:
  by: claude-code/opus-5
  at: 2026-08-15T00:00:00Z
sources:
- .claude/skills/verify/SKILL.md
- .claude/skills/ship/SKILL.md
---

# Verification in the main loop

## Purpose

The workspace skills form a loop — explore → plan → implement → ship — but
verification sits outside it as a fifth skill the user has to remember to
invoke, at the right moment. It should be a step the loop performs.

Ship's step 1 says to confirm the plan's `## Verification` section "against
reality (test output, the diff, a manual check)" and names verify as "the
thorough form of this step". That names verify without invoking it. Whether
verification actually happens, and how rigorously, is left to the agent's
discretion at ship time — and the cheapest reading of step 1 ("check the diff")
satisfies it without ever tracing a requirement to code, checking scenario
coverage, or testing the plan against `## Approach` and `## Out of scope`.

So two ships of identically-implemented work can differ entirely in how much was
confirmed, with nothing distinguishing them afterwards. The gap is not that
verify results are fragile — it is that nothing compels them to exist.

## Behaviour

**Ship invokes verify.** Step 1 stops being "confirm by some means" and becomes
"run the verify skill; refuse to proceed on any CRITICAL". Verify's report lands
in ship's own context and is consumed immediately, so nothing needs to persist
between the two — the volatility of a verify report is irrelevant when the same
invocation that produces it also acts on it.

This keeps the loop at four steps, makes verification non-optional, and makes
the refusal mechanical rather than advisory.

Properties that should hold:

- Shipping a plan with unmet CRITICALs is refused, not merely discouraged.
- Verify stays independently invocable — mid-implementation, or in audit mode —
  without shipping anything.
- Verify keeps writing nothing to the graph. Its report is consumed by ship in
  the same turn; "Report, never fix" is unaffected.

**Alternative — verify at both ends.** Implement runs verify before reporting a
plan complete, and ship runs it again before flipping stages. Catches drift
earlier, while the context to fix it is still loaded. Costs duplicated work when
implement and ship land in one session, and leaves two call sites to keep in
sync. Not exclusive with the above; see `## Open questions`.

## Edge cases

- **Cancelled plans skip ahead.** Ship's step 3 allows `stage=cancelled` and
  stops there. Abandoning a plan should not require a clean verify.
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

## Open questions

- Ship-invokes-verify alone, or verify at both ends of implement and ship? The
  trade turns on how often implement and ship land in the same session, which is
  not measured today.
- Should the CRITICAL refusal be overridable by explicit user instruction, and
  should an override be recorded in `data/log.md`?
- Does implement gain anything from a scoped verify (its own tasks only) that
  ship's full verify would not already catch?
