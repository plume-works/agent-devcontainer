---
type: bug
description: When claude-remote-control-start.sh succeeds but the claude-remote pane exits before the watcher's live check, the standalone Remote Control watcher re-runs the start every interval, with two claude auth status calls each time, and never reaches the controller's recovery budget.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T03:45:25Z
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/remote_control.py
- resource: scripts/tests/test_runtime_remote_control.py
- resource: docs/knowledge/data/plans/20261027-standalone-remote-control-autostart.md
---

# Bug: the Remote Control watcher restarts a session that never comes up on every tick

## Symptom

With a claude.ai login, if the `claude-remote` pane exits before the watcher
checks for it, `runtime-remote-control.sh run` starts it again on every
`AGENTDEV_HEALTH_INTERVAL`, indefinitely. Each pass runs
`claude-remote-control-start.sh` and two `claude auth status` processes, one in
the watcher and one in the start script. The watcher never exits, so the
controller's bounded recovery never applies and the runtime never reports
`remote-control` degraded. The status file is not rewritten: it is missing on a
first start, or keeps `waiting for a claude.ai login` when the login arrived
after the watcher started.

## Reproduction

Using the `Watch` harness in `scripts/tests/test_runtime_remote_control.py`,
replace the fake `tmux` with one whose `new-session` succeeds but whose
`has-session` always fails, as a pane that exits at once would leave it; then
log in and start the watcher with `AGENTDEV_HEALTH_INTERVAL=0.1`. After 3 s: 25
starts, 50 `claude auth status` calls, an empty status, and the watcher still
running (2026-10-28).

A real pane exits that fast when its `claude` process fails at once, before
`live` runs right after the start script returns. A pane that lives long enough
for one `live` check is handled: the next tick sees it gone and the watcher
exits non-zero.

## Root cause

When the start script returns 0 and `live` fails, the watcher treats it as "not
started yet": it clears `checked` so the next tick re-reads the login and
retries the start, without setting `seen` or exiting. The start script also
returns 0 when it skips startup, so a 0 exit does not mean a session was
created; the watcher cannot tell "skipped" from "started and died", and neither
case is bounded.

## Fix

A start that leaves no live session now ends the watcher non-zero, logging that
the session did not come up, as a seen session that disappears already does; the
controller's recovery budget bounds the retries. The retry that cleared
`checked` is gone. `test_a_start_that_never_comes_up_ends_the_watcher` in
`scripts/tests/test_runtime_remote_control.py` covers it: one start, then a
non-zero exit.

## Key references

Verified anchor points (line numbers as of 2026-10-31):

- `py_packages/agentdev_runtime/agentdev_runtime/remote_control.py:240` — `run`:
  login re-check when the credential signature changes
- `py_packages/agentdev_runtime/agentdev_runtime/remote_control.py:249` — a seen
  session that is gone ends the watcher
- `py_packages/agentdev_runtime/agentdev_runtime/remote_control.py:253` — the
  `start()` call
- `py_packages/agentdev_runtime/agentdev_runtime/remote_control.py:257` — a
  start that leaves no live session ends the watcher
- `py_packages/agentdev_runtime/agentdev_runtime/remote_control.py:115` —
  `start`'s own `claude auth status` check, which returns 0 when it skips
- `py_packages/agentdev_runtime/agentdev_runtime/remote_control.py:143` —
  `tmux new-session`, which returns before the pane's process runs
