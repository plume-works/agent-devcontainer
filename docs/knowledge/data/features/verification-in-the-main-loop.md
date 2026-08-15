---
type: feature
stage: proposed
status: draft
description: Make verification a step the main workflow loop performs, rather than a separate skill whose results survive only in conversation context.
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
invoke, at the right moment, in the right session. That placement has a
concrete failure mode.

Verify's output is a report. It writes nothing to the graph; its own rules
forbid that ("Report, never fix"). So a verify result exists only in the
conversation context of the session that produced it. Ship's step 1 asks the
agent to confirm the plan's `## Verification` section "against reality (test
output, the diff, a manual check)" and names verify as "the thorough form of
this step" — but a `/ship` invoked in a fresh session has no access to an
earlier session's verify. It cannot distinguish *verified clean an hour ago*
from *never checked at all*, and the cheapest way to satisfy step 1 from a cold
start is the weakest one.

The result is that the rigor of shipping depends on session boundaries rather
than on the work. Two sessions that did identical implementation work can ship
with very different levels of confirmation, and nothing in the graph records
which happened.

## Behaviour

Two designs were raised. They are not exclusive, and the choice between them is
open — see `## Open questions`.

**Option A — ship calls verify.** Ship's step 1 stops being "check the
`## Verification` section by some means" and becomes "run verify; refuse on
CRITICAL". The loop returns to four steps, verification becomes non-optional,
and a cold-start `/ship` is as rigorous as a warm one. Cost: every ship pays
full verify latency, including the requirement-tracing and coherence passes,
even for a plan whose verification is three green commands.

**Option B — verify at both ends.** Implement runs verify before it reports a
plan complete; ship runs it again before flipping stages. Catches drift earlier,
when the context to fix it is still loaded, and keeps the two invocations cheap
by letting each check only what its phase can affect. Cost: duplicated work when
implement and ship happen in one session, and two places to keep in sync.

Either way, three properties should hold:

- Shipping a plan with unmet CRITICALs is refused, not merely discouraged.
- A verify result is durable enough that a later session can tell whether one
  happened and what it concluded — otherwise Option A only moves the
  session-boundary problem from ship to whoever reads the report.
- The user can still invoke verify standalone, mid-implementation, without
  shipping anything.

## Edge cases

- **Verify is currently forbidden to write.** Any durable record of a verify
  result — a frontmatter field, a log entry, a report artifact — contradicts
  "Report, never fix" as written. That rule exists to keep the audit trail
  clean, and its scope would need revisiting rather than quiet violation.
- **The plan schema has no verified state.** `stage` takes `done | cancelled`
  only, omitted while active. Recording verification needs either a new field or
  a deliberate decision to keep it out of frontmatter.
- **A stale verify is worse than none.** If a result is made durable, it must be
  invalidated by subsequent commits to the plan's sources; otherwise ship trusts
  a check that predates the code it is shipping.
- **Audit mode has no plan.** Verify's audit mode sweeps the whole graph and is
  not tied to a plan or a ship, so whatever coupling is added must leave that
  entry point intact.
- **Cancelled plans skip ahead.** Ship's step 3 allows `stage=cancelled` and
  stops there; that path should not require a clean verify.

## Open questions

- Option A, Option B, or both? The cost/benefit turns on how often implement and
  ship land in the same session, which is not measured today.
- Should a verify result be recorded in the graph at all, and if so where — plan
  frontmatter, `data/log.md`, or a report document under a new path?
- What invalidates a recorded verify result — any commit touching the plan's
  `sources`, or a coarser signal?
- Should ship's refusal on CRITICAL be overridable with an explicit user
  override, and should that override be logged?
