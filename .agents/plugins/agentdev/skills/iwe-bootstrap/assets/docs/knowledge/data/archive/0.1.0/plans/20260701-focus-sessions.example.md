---
type: plan
description: 'Example shipped plan: building focus sessions, from approach through completion.'
stage: done
created: 2026-07-01
completed: 2026-07-18
---

# Focus sessions

*Example document — this shows the full body template of a shipped plan,
including the `## Spec changes` section the ship skill synced before flipping
the stage to done and moving the plan to `archive/0.1.0/plans/`. The setup skill
deletes `*.example.md` files after onboarding.*

## Context

Pomodux has a window and a session log but no working timer. This plan builds
the core loop: countdown, pause/resume, completion logging. The session log
([timer rationale](../../../spec/timer.example)) is already in place.

## Approach

A pure timer engine driven by a monotonic clock, decoupled from the UI: the
engine emits state transitions, the store reduces them, the UI renders the
store. Completion appends to the session log through the existing writer.

## Implementation Steps

### Task 1: Timer engine

**Files:** Create: `src/timer/engine.ts`, `src/timer/engine.test.ts`

- [x] Countdown state machine (idle → running → paused → completed/abandoned)
- [x] Monotonic elapsed-time computation
- [x] Unit tests for every transition

### Task 2: Store and log integration

**Files:** Modify: `src/store/sessions.ts`, `src/store/reducers.ts`

- [x] Reduce engine transitions into store state
- [x] Append completed and abandoned sessions to the log
- [x] Discard sessions shorter than one minute

### Task 3: UI wiring

**Files:** Create: `src/ui/timer-view.tsx`; Modify: `src/ui/tray.ts`

- [x] Main-window countdown display with start/pause/resume/abandon
- [x] Tray controls mirroring the window
- [x] Completion chime

## Spec changes

[Timer](../../../spec/timer.example) — session countdown, pause/resume, and
wall-clock independence requirements written from this plan's behavior.

## Verification

- `npm test` — engine transitions and reducer coverage green.
- Manual: 25-minute session with a mid-session pause completes and appears in
  the history log; abandoning logs with the `abandoned` flag.

## Out of scope

- Break timers and long-break scheduling.
- The streak widget (planned separately).

## Key references

- `src/store/sessions.ts::appendSession` — the log writer
- `src/main.ts::bootstrap` — window/tray bootstrap where the view mounts

*Convention notes: `stage: done` requires `completed` (schema-enforced), and a
shipped plan carries no `rank`. Ship moved it out of the plans hub into the
archive; the release cut moved it from `next-release` to `0.1.0`.
`## Spec changes` names every spec this work touches — the ship skill walks that
list before the stage flips, which is what keeps specs from drifting.*
