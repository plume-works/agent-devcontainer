---
type: task
stage: done
completed: 2026-10-27
priority: medium
created: 2026-10-27
description: Find the root cause of the intermittent test_recovery_kills_what_a_crashed_service_left_in_its_group failure, starting from the unreaped-zombie hypothesis, and record it in the bug.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-27T18:00:00Z
sources:
- resource: docs/knowledge/data/bugs/supervision-orphan-kill-test-flaky.md
- resource: scripts/tests/test_agent_runtime_supervision.py
- resource: .devcontainer/scripts/runtime-supervisor.py
---

# Find why the orphan-kill supervision test is flaky

[Orphan-kill supervision test fails
intermittently](../bugs/supervision-orphan-kill-test-flaky.md) has a
reproduction but no root cause. Until it has one, an intermittent red on the
supervision suite cannot be told apart from a real regression in the
controller's process-group kill, which is what keeps a crashed Xpra from holding
the display.

## What to do

- Test the bug's leading hypothesis: at the failing assertion, read the orphan's
  state from `/proc/<pid>/stat`. A `Z` state means the kill worked and the
  orphan is waiting to be reaped; a live state means the group kill missed it.
- Record what is eliminated, and the cause once found, in the bug's
  `## Root cause`, then decide the fix there: change the test, the controller,
  or both.

## Done when

The bug's `## Root cause` names the cause with the evidence that confirms it,
and its `## Fix` states the chosen fix or a recorded decision not to fix.
