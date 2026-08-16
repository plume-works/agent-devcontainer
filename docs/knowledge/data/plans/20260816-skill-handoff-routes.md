---
type: plan
created: 2026-08-16
description: Give explore a destination for a defect it establishes, and give verify's unchecked-box CRITICAL the third route that ship's no-override rule now requires.
generated:
  by: claude-code/opus-5
  at: 2026-08-16T00:00:00Z
sources:
- .claude/skills/explore/SKILL.md
- .claude/skills/verify/SKILL.md
- .claude/skills/ship/SKILL.md
- .claude/skills/plan/SKILL.md
- docs/knowledge/data/features/verification-in-the-main-loop.md
---

# Name the missing handoff routes in explore and verify

## Context

An exploration compared OpenSpec's explore → propose → apply → archive prompts
with this workspace's explore → plan → implement → ship skills, looking for
language worth adopting. Ten candidate borrowings came out of it; eight landed
in `0d4d37b`, `61cce13`, and `fcdd45a`. Two remain, and both have the same shape
as [Missing map skill](../bugs/missing-map-skill.md): a skill detects something
it is not allowed to fix, and names no owner.

**Explore can find a defect and has nowhere to put it.** Its `## Capturing` list
routes an idea, a design insight, a principle, and readiness to build. A defect
is absent — so an exploration that establishes that a `data/spec/` doc no longer
matches the code has no destination for that finding. `## During implementation`
covers the case where a plan is already in flight; outside that, the finding
dies with the conversation.

**Verify's unchecked-box recommendation is no longer exhaustive.** It reads
"complete it, or tick it if already done". Since
[Verification in the main loop](../features/verification-in-the-main-loop.md)
made a zero-CRITICAL Verify report a hard precondition of normal Ship —
`.claude/skills/ship/SKILL.md:40`, "there is no CRITICAL override" — a task the
user has decided not to do now blocks shipping outright. Ticking it is forbidden
by `.claude/skills/implement/SKILL.md:57-60`, and completing it is exactly what
the user declined. That feature's resolved decisions name two ways out, fix or
cancel the whole plan; revising the plan to drop the task is the proportionate
third, and no skill mentions it.

## Approach

Two prose edits and one coherence fix. No new skills, no new sections, no change
to any skill's existing boundary: explore still files nothing unprompted, and
verify still reports rather than revises.

Explore gains one `## Capturing` bullet routing an established defect to
`data/bugs/<slug>.md` — the lane the Record step of `docs/knowledge/AGENTS.md`
already specifies for a found defect, and the lane
[Missing map skill](../bugs/missing-map-skill.md) itself used for a doc-level
one. Ship was the other candidate, since it owns spec merges after `fcdd45a`,
and it was rejected: ship acts only on a selected plan's `## Spec changes`, so a
spec-versus-code contradiction found with no plan in flight has nothing for ship
to attach to. [Write a capture skill](../backlog/capture-skill.md) may later own
this lane properly; the bullet is worded so that task can absorb it rather than
have to contradict it.

Verify's existing recommendation gains the third route, pointing at the plan
skill's revise mode and inheriting its materiality test rather than inventing a
parallel one — dropping a task changes scope, so
`.claude/skills/plan/SKILL.md:32-37` already requires user direction for it. The
rejected alternative was softening ship's no-override rule, which is the
explicit resolved decision of an implemented feature and not this plan's to
reverse.

The feature doc is updated in the same plan because leaving it listing two
routes while verify lists three creates precisely the doc↔code drift verify's
own audit mode exists to catch.

## Implementation Steps

### Task 1: Explore routes a defect it establishes

**Files:** Modify: `.claude/skills/explore/SKILL.md`

- [x] **1. Add the defect destination to `## Capturing`.** Insert a bullet after
  the principle bullet (`.claude/skills/explore/SKILL.md:57-58`) and before
  "Ready to build": a defect the exploration established — code that contradicts
  a `data/spec/` doc, or any reproducible wrong behavior — goes to
  `data/bugs/<slug>.md` in the Symptom / Reproduction / Root cause / Fix shape
  with `path:line` anchors, linked from `data/bugs.md`. Name the boundary with
  `## During implementation` (`.claude/skills/explore/SKILL.md:39-45`) so a
  finding that belongs to a plan already in flight is handed back to plan or
  implement instead of becoming a bug doc. Preserve the section's "offer once —
  don't file unprompted" discipline; this adds a destination, not an obligation.

### Task 2: Verify names the third route

**Files:** Modify: `.claude/skills/verify/SKILL.md`

- [x] **2. Extend the unchecked-box recommendation to three routes.** At
  `.claude/skills/verify/SKILL.md:25-26`, keep the CRITICAL severity and the two
  existing routes, and add the third: revise the plan to drop the task, via the
  plan skill's revise mode, which treats dropping a task as a material scope
  change needing user direction. State why the third route exists — ship refuses
  any CRITICAL with no override, so an unchecked task the user has decided
  against is otherwise unshippable — so the rule survives editing. Keep "Report,
  never fix" intact: verify names the route, it does not take it.

### Task 3: The feature doc lists the same routes as the skill

**Files:** Modify:
`docs/knowledge/data/features/verification-in-the-main-loop.md`

- [ ] **3. Add the revision route to `## Resolved decisions`.** That section
  currently reads that a plan with a CRITICAL "remains active for fixes or can
  be explicitly cancelled". Add revising the plan to drop the task as the third
  outcome, so the feature doc and Task 2's recommendation agree. Keep
  `stage: implemented` — this records a route the implemented coupling already
  permits, not new behavior.

## Spec changes

None — no behavioral change to the published product. The workspace skills under
`.claude/skills/` have no `data/spec/` doc, and neither does the ship↔verify
coupling
([Verification in the main loop](../features/verification-in-the-main-loop.md)
is an implemented feature carrying its own behaviour and edge cases). Writing a
durable spec for two routing bullets would be ceremony out of proportion to the
risk, and would duplicate what that feature doc already owns.

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  reports every skill valid with 0 errors and 0 warnings — the same result it
  gave on the unmodified checkout on 2026-08-16, so any regression is this
  change's. The skill count itself is not the assertion: the command walks `.`,
  so scratch skills under `.tmp/` change the denominator (46 on a clean tree, 47
  with one such artifact present) without meaning anything.
- `iwe normalize` followed by `iwe schema validate` exits 0.
- `uv run pre-commit run --all-files` passes.
- Read-back of `.claude/skills/explore/SKILL.md`: `## Capturing` names a
  destination for a defect, and nothing in it contradicts
  `## During implementation` about which findings become bug docs.
- Read-back of `.claude/skills/verify/SKILL.md`: the unchecked-box
  recommendation lists three routes, the third defers to the plan skill's
  materiality test rather than restating one, and the surrounding CRITICAL
  severity and "Report, never fix" rule are unchanged.
- Read-back of the feature doc: its resolved decisions and verify's
  recommendation name the same set of outcomes.

## Out of scope

- **The ticked-box asymmetry.** Verify still takes a `- [x]` on faith, which is
  the defect in
  [Plan checkbox over-claiming](../bugs/plan-checkbox-over-claiming.md) and is
  owned by
  [Make plan checkboxes carry their evidence](20260815-honest-plan-checkboxes.md).
  That plan is unstarted and its anchors are stale after `0d4d37b`, `61cce13`,
  and `fcdd45a`; it needs a revise pass before implementation. Its Task 1
  appends to verify's Completeness dimension immediately after the lines Task 2
  here edits — adjacent, not conflicting, and the two can land in either order.
- **Softening ship's no-CRITICAL-override rule**, which is a resolved decision
  of an implemented feature.
- **A capture skill** owning the backlog, bug, and proposed-feature inbox lanes
  ([Write a capture skill](../backlog/capture-skill.md)). Task 1 adds one
  destination to explore; it does not build the general lane owner.
- **The missing map skill** ([Missing map skill](../bugs/missing-map-skill.md)),
  the same "detects but cannot fix" shape, whose fix is upstream.
- Any further OpenSpec borrowing; the remaining eight either landed or were
  deliberately rejected during the exploration.

## Key references

Verified anchor points (line numbers as of 2026-08-16):

- `.claude/skills/explore/SKILL.md:47-62` — `## Capturing`, its four destination
  bullets and the closing validate line
- `.claude/skills/explore/SKILL.md:39-45` — `## During implementation`, the
  plan-in-flight handoff Task 1 must not contradict
- `.claude/skills/verify/SKILL.md:25-26` — the unchecked-box CRITICAL and its
  two-route recommendation
- `.claude/skills/verify/SKILL.md:68-69` — "Report, never fix", the boundary
  Task 2 preserves
- `.claude/skills/verify/SKILL.md:70-71` — zero CRITICAL as Ship's required
  handoff
- `.claude/skills/ship/SKILL.md:35-41` — Ship step 3, "there is no CRITICAL
  override"
- `.claude/skills/implement/SKILL.md:57-60` — the rule forbidding a tick for
  deferred behavior, which closes the second route
- `.claude/skills/plan/SKILL.md:23-30` — revise mode and its materially-same
  test
- `.claude/skills/plan/SKILL.md:32-37` — the materiality definition a dropped
  task must clear
