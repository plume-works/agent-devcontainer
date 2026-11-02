---
type: bug
description: Under pytest-xdist, the two real-tmux Remote Control start tests share one claude-remote tmux server, so one test sees the other's session as already running, or its teardown kills it, before the fake claude records a result.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-02T04:00:00Z
sources:
- resource: scripts/tests/test_claude_remote_control_start.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/remote_control.py
- resource: https://github.com/plume-works/agent-devcontainer/actions/runs/41380787079/job/125074211772
---

# Bug: Remote Control real-tmux tests share one tmux server under pytest-xdist

## Symptom

CI's pytest run, under `-n` workers, intermittently fails
`test_claude_remote_control_start.py::test_real_tmux_starts_claude_without_setup_token[True]`
with `FileNotFoundError` on its `result` file, after the `returncode == 0`
assertion has passed. The rest of the suite passes, and the failure is unrelated
to the diff under test.

## Reproduction

Run `scripts/tests` under pytest-xdist so the `[False]` and `[True]`
parametrizations land on different workers within the same 10 seconds. It is
timing-dependent; neither variant fails when run alone.

## Root cause

Both parametrizations set `TMUX_TMPDIR` to the shared `TMP_ROOT`, and `start()`
always uses the fixed server `tmux -L claude-remote` with the session
`claude-remote`, so concurrent variants reach the same server:

- When one variant's fake claude is still sleeping in `claude-remote`, the other
  variant's `start()` finds `live()` true, prints that the session is already
  running, and returns 0 without launching its own claude, so its `result` file
  is never written. This is the failure CI shows.
- Each variant's teardown runs `kill-server` on both the default socket and
  `-L claude-remote`, which can kill the other variant's keeper or session
  before its fake claude writes the result.

The result poll also allows only 3 seconds, little on a loaded host. This is the
same defect as
[opencode-web-tmux-shared-under-xdist](opencode-web-tmux-shared-under-xdist.md),
whose fix covered only `test_opencode_web_start.py`.

## Fix

Not yet fixed. Set `TMUX_TMPDIR` to the test's own scratch directory so each
variant gets private default and `claude-remote` servers, and allow the result
poll 10 seconds. The `[True]` variant must keep its keeper on the default socket
under that directory: it covers the `data/spec/claude-remote-control` scenario
in which a tmux server is live on the default socket before the command runs.

## Key references

Verified anchor points (line numbers as of 2026-11-02):

- `scripts/tests/test_claude_remote_control_start.py:210` —
  `test_real_tmux_starts_claude_without_setup_token`
- `scripts/tests/test_claude_remote_control_start.py:213` — shared
  `tmux_dir = TMP_ROOT`
- `scripts/tests/test_claude_remote_control_start.py:245` — 3-second result poll
- `scripts/tests/test_claude_remote_control_start.py:253` — teardown
  `kill-server` on both sockets
- `py_packages/agentdev_runtime/agentdev_runtime/remote_control.py:25` —
  `SESSION = 'claude-remote'`
- `py_packages/agentdev_runtime/agentdev_runtime/remote_control.py:132` —
  `start()` returns early when `live()`
- `scripts/tests/scratch.py:5` — `TMP_ROOT`, shared by every worker
