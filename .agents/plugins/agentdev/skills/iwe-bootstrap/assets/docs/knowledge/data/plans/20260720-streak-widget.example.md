---
type: plan
description: 'Example active plan: building the streak widget.'
created: 2026-07-20
rank: 500
release:
- features/streak-widget.example
---

# Streak widget

*Example document — this shows an active plan (no `stage` frontmatter) with a
`## Depends on` section. The setup skill deletes `*.example.md` files after
onboarding.*

## Context

The [streak widget feature](../features/streak-widget.example) is proposed: an
always-on-top widget showing the daily focus streak. Streaks are derived from
the session log at read time — no new stored state.

## Approach

A pure `computeStreak(log, timezone)` function over the session log, rendered in
a small frameless window. Day boundaries come from local midnight at session
completion time so timezone changes never double-count.

## Implementation Steps

### Task 1: Streak derivation

**Files:** Create: `src/store/streak.ts`, `src/store/streak.test.ts`

- [ ] `computeStreak` over the session log
- [ ] Timezone-change and DST test cases

### Task 2: Widget window

**Files:** Create: `src/ui/widgets/streak.tsx`; Modify: `src/main.ts`

- [ ] Frameless always-on-top window, click opens history
- [ ] No notifications, no negative framing (concept constraint)

## Acceptance

### Scenario: A day without a session restarts the streak

- **WHEN** the session log has sessions on Monday and Wednesday and none on
  Tuesday
- **THEN** `computeStreak` on Wednesday returns 1
- **Test:** `src/store/streak.test.ts::restarts after a skipped day`

### Scenario: A time zone change does not count a day twice

- **WHEN** the user completes a session, moves three time zones west, and
  completes another session on the same local day
- **THEN** `computeStreak` counts that day once
- **Test:**
  `src/store/streak.test.ts::counts a day once across a time zone change`

## Depends on

Requires the session log populated by [Focus
sessions](../archive/0.1.0/plans/20260701-focus-sessions.example) — streaks
derive from completed sessions.

## Verification

- Unit tests cover streak derivation across timezone changes.
- Manual: complete a session, widget shows day 1; simulate a skipped day, streak
  restarts at zero without any alert.

## Out of scope

- Weekly/monthly aggregates in the history view.

*Convention notes: an active plan simply has no `stage`, and its `rank` places
it in the build order that
`iwe find --filter '{rank: {$exists: true}}' --sort rank:1` lists.
`## Depends on` uses inline links (soft references), so the dependency is
queryable via `iwe find --references` without making this plan a child of the
other. Each `## Acceptance` scenario names the test that proves it; Verify runs
that test before Ship.*
