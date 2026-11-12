---
type: spec
description: 'Example specification: the timer''s required behaviour as SHALL requirements and WHEN/THEN scenarios.'
---

# Timer

*Example document — this shows the shape of a behavioral spec:
`### Requirement:` sections with SHALL statements, each backed by
`#### Scenario:` WHEN/THEN examples concrete enough to test. The setup skill
deletes `*.example.md` files after onboarding.*

How the Pomodux countdown timer must behave. This is the durable truth the
implementation is checked against; when a shipped plan changes timer behavior,
this document is updated in the same change.

## Requirements

### Requirement: Session countdown

The timer SHALL count down a focus session of the configured length and end it
with a completion signal, independent of UI state.

#### Scenario: Starting a focus session

- **WHEN** the user starts a focus session with a 25-minute setting
- **THEN** the timer counts down from 25:00 and fires the completion signal at
  00:00
- **AND** the completion is recorded even if the window is closed or minimized

### Requirement: Pause and resume

The timer SHALL pause and resume without losing elapsed time.

#### Scenario: Resuming a paused session

- **GIVEN** a session paused at 12:34 remaining
- **WHEN** the user resumes
- **THEN** the countdown continues from 12:34

### Requirement: Wall-clock independence

Elapsed time SHALL be computed from a monotonic clock, so system sleep, timezone
changes, or manual clock adjustments never corrupt a session.

#### Scenario: Laptop sleeps mid-session

- **GIVEN** a running session with 10:00 remaining
- **WHEN** the machine sleeps for an hour and wakes
- **THEN** the session is either completed (if configured to run through sleep)
  or paused at 10:00 — never showing negative or drifted time

## Rationale

Completed sessions append to a JSON-lines log in the user data directory, and
aggregates such as daily totals and streaks are derived at read time. Sessions
are immutable facts, crash recovery reduces to replaying the file, and sync
between machines becomes a merge of two logs.

Rejected:

- **SQLite** — transactional power the timer does not need, and a native
  dependency in an otherwise pure-TypeScript build.
- **A mutable JSON snapshot** — a crash during a write can lose the whole
  history, not just the last entry.

*Convention notes: specs carry `type: spec` and no stage — they are reference,
not work items. The requirement headers are stable names other documents cite:
the [timer drift bug](../bugs/timer-drift-after-sleep.example) reports a
violation of "Wall-clock independence", and the [focus sessions
plan](../archive/0.1.0/plans/20260701-focus-sessions.example) lists this spec
under its `## Spec changes`. `## Rationale` holds the decision behind the
behaviour and the alternatives it rejected, and states no behaviour itself.
Scale rigor with risk — a two-line requirement is fine for low-risk behavior.*
