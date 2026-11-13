---
type: plan
description: 'Example shipped plan: building focus sessions, from approach through completion.'
stage: done
created: 2026-07-01
completed: 2026-07-18
---

# Focus sessions

*Example document — this shows the full body template of a shipped plan,
including the `## Acceptance` scenarios Verify checked before the ship skill set
the stage to done and moved the plan to `archive/0.1.0/plans/`. The setup skill
deletes `*.example.md` files after onboarding.*

## Context

Pomodux has a window and a session log but no working timer. This plan builds
the core loop: countdown, pause/resume, completion logging. The session log is
already in place.

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

## Acceptance

### Scenario: A focus session ends at 00:00

- **WHEN** the user starts a focus session with a 25-minute setting and closes
  the window
- **THEN** the timer fires the completion signal at 00:00 and records the
  session
- **Test:** `src/timer/engine.test.ts::completes with the window closed`

### Scenario: A paused session resumes where it stopped

- **WHEN** the user resumes a session paused at 12:34 remaining
- **THEN** the countdown continues from 12:34
- **Test:** `src/timer/engine.test.ts::resumes from the paused time`

### Scenario: Sleep does not corrupt a session

- **WHEN** the machine sleeps for an hour during a session with 10:00 remaining
- **THEN** the session shows no negative or incorrect time when the machine
  wakes
- **Test:** `src/timer/engine.test.ts::survives sleep`

## ADRs

[The timer counts wall-clock
time](../../../adr/0001-timer-counts-wall-clock-time.example)

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
archive; the release cut moved it from `next-release` to `0.1.0`. Each
`## Acceptance` scenario names the test that proves it, and Ship set the ADR
that `## ADRs` links to `stage: accepted`.*
