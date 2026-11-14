---
type: adr
stage: accepted
description: 'Example decision record: a focus session lasts its length in real time, also while the laptop sleeps.'
---

# The timer counts wall-clock time

A user who starts a 25-minute session expects it to end 25 minutes later, also
when the laptop sleeps. The timer counts the real time that passes, from a
monotonic clock that includes sleep. A session that stops during sleep ends
later than the user expects, and a clock change must not move its end.

## Considered Options

- Pause the session while the laptop sleeps. Rejected: the session ends later
  than the time the user saw at its start.
- Compute elapsed time from `Date.now()` deltas. Rejected: a manual clock change
  or a time zone change corrupts the session.
