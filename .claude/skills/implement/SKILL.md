---
name: implement
description: Execute an active plan task-by-task with state discipline — verified anchors, tests before checkbox ticks, clean stopping points, deviations written back into the plan. Use when the user says "implement <plan>", "continue the plan", "work on the next task", or asks to start building something that already has a plan.
---

# Implement a plan

Coding happens as it always does; this skill adds the discipline that keeps
the plan document true while it happens. The plan is the source of truth: the
code follows it, and where reality wins an argument, the plan is updated —
never silently outgrown. A plan statement, prior checkbox, or contextual claim
is not proof that behavior exists; current code and passing task evidence are.

## Steps

1. **Select the plan.** Infer from conversation; if ambiguous, list the plans
   under `## Active` in `data/plans.md` and ask (most recently created first).
   Announce: "Working on: <plan> — task N of M". No plan exists for what the
   user wants built? Stop and point at the plan skill.
2. **Load the context.** Read the full plan, the specs in its
   `## Spec changes`, and `data/product.md` `## Constraints` and
   `## Authoring rules` — they bind the code you're about to write. Note which
   form the plan's spec impact takes — an explicit `None`, a concise normative
   outcome, or a fenced `ADDED` / `MODIFIED` / `REMOVED` delta — and read it
   against the current durable spec. The recorded form is the behavior this
   work is meant to produce; the durable spec is what remains true until Ship
   merges that intent. Both bind the code, and where they differ, the
   difference is the work.
3. **Check `## Depends on`.** Every prerequisite plan must carry
   `stage: done`; if one doesn't, say so and stop — building on an unshipped
   dependency is how two plans end up half-true.
4. **Re-verify the anchors.** The plan's `## Key references` line numbers were
   true when written; re-locate each symbol in the current checkout before
   relying on it. If lines moved, update the anchor list and its
   "verified as of" date — that edit is part of this session's work.
5. **Execute the next unchecked task.** Follow its `**Files:**` list; write
   the code; run every test and check required for that task. Closing it is a
   single edit that ticks `- [ ]` → `- [x]` _and_ writes the task's indented
   `- **Evidence:**` child naming what closed it — the commit, the test run and
   its result, the CI run — specifically enough that a later session can go
   look. Do it only when the task's complete specified behavior is implemented
   with passing evidence, then run `iwe normalize`. Partial work, deferred
   behavior, or a failing required test or check stays unchecked, with no
   evidence line. If you cannot name the evidence, the box is not closable:
   that is the check working, not a formatting obstacle.
6. **Classify deviations before coding past them.** A change is material when
   it affects scope, externally observable behavior, compatibility, acceptance
   criteria, dependencies, or an explicit out-of-scope boundary.
   - **Tactical correction:** if a stale anchor, task breakdown, or other plan
     detail can be corrected while preserving intent and every material
     boundary, update the plan first, report the correction and why it
     preserves intent, then continue within the user's requested task boundary.
     The plan's recorded spec impact is one of those boundaries: a correction
     may proceed only while the recorded behavioral outcome still holds exactly
     as written.
   - **Material deviation:** if completing the task would add scope or drop,
     narrow, defer, or accept an exception to specified behavior, leave the
     task unchecked. Explain the needed change and wait for user direction
     before changing the plan or coding beyond it. Any change to a recorded
     normative outcome, delta operation, requirement, or scenario is material
     by definition — never edit the delta to match what you built. It goes back
     through the plan skill's revise mode, with the user's direction, before
     coding continues.
7. **Stop at a clean boundary.** After each task (or more, if the user asked
   for a longer run), report progress — "3/5 tasks, next: <task name>" — plus
   the actual code changed and tests/checks run as evidence, and stop. Blocked
   or incomplete mid-task? Leave the box unchecked, describe the remaining
   work or failing evidence, and stop there instead.
8. **Finish.** When the last box ticks, run the plan's `## Verification`
   commands, report the results, and suggest the verify skill for the full
   pre-ship check, then the ship skill.

## Capturing what implementation turns up

Implementation produces findings the plan never anticipated, and they are often
the most expensive knowledge in the session. They do not belong in the plan.
Each has a home:

- A durable design fact — a constraint, a boundary, why the obvious approach
  fails → `data/architecture/<slug>.md`, linked from `data/architecture.md`.
  Add to the existing doc that owns the area before creating a new one.
- A defect in shipped behavior, not caused by this work →
  `data/bugs/<slug>.md` (Symptom / Reproduction / Root cause / Fix, with
  `path:line` anchors), linked from `data/bugs.md`.
- Work this plan should not absorb → `data/backlog/<slug>.md`, and say so in
  the handoff report rather than growing `## Out of scope` silently.
- A finding that changes a material boundary → stop and take it back through
  the plan skill (Step 6), which is the only route that may edit intent.

`## Context` and `## Approach` state intent and stay stable while you build.
The plan skill owns them; implement edits them only via Step 6's material
deviation route. Writing a finding into them, rather than routing it, is the
most common way a plan stops being executable — it grows to where a future
session cannot tell what was planned from what merely happened.

Reproducing a finding is normal work: a harness, a script, an ablation. The
harness is code and lives in the repository. Its _output_ is not plan content.

## Rules

- Never tick a box for partially implemented or deferred behavior, or when a
  required test or check fails or was not run — an unchecked box that's
  actually done is a nuisance; a checked box that isn't done is a lie the next
  session builds on.
- One edit never changes more than one checkbox. A blanket `- [ ]` → `- [x]`
  substitution across the file is itself the defect, not a faster route to the
  same result: eight verified ticks and one careless sweep produce identical
  bytes, and only the per-box evidence line tells them apart.
- Checkbox flips, their evidence lines, and anchor updates belong in the same
  commit as the code they describe.
- One task at a time unless the user asks for more; small honest increments
  beat a big unreviewable one.
- Never silently expand the plan or narrow its specified behavior to fit the
  implementation. Material changes require user direction before coding.
- This skill implements; it doesn't ship. Status flips, spec sync, and release
  recording stay with the ship skill.
