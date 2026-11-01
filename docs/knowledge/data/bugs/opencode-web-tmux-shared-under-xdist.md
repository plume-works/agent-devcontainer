---
type: bug
stage: done
description: Under pytest-xdist, the real-tmux opencode-web tests shared one tmux server socket, so one test's teardown killed the other's server before its fake opencode recorded a result.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T21:10:00Z
sources:
- resource: scripts/tests/test_opencode_web_start.py
---

# Bug: opencode-web real-tmux tests share one tmux server under pytest-xdist

## Symptom

`uv run pytest -n 8 scripts/tests` fails
`test_opencode_web_start.py::test_real_tmux_passes_the_password_and_drops_display`
with `FileNotFoundError` on its `result` file. The file passes when run alone.

## Reproduction

Run `scripts/tests/test_opencode_web_start.py` under `-n 8` alongside the rest
of `scripts/tests`, so the two real-tmux tests land on different workers at the
same time.

## Root cause

`run_with_real_tmux` set `TMUX_TMPDIR` to the shared `TMP_ROOT`, so every
worker's `tmux -L opencode` reached the same server, and each test's teardown
runs `tmux -L opencode kill-server`. One test's teardown killed the server the
other had just started. The result poll also allowed only 3 seconds, little on a
loaded host.

## Fix

`TMUX_TMPDIR` is the test's own scratch directory, so each test gets its own
server, and the poll allows 10 seconds; it still returns as soon as the result
appears.

## Key references

Verified anchor points (line numbers as of 2026-10-31):

- `scripts/tests/test_opencode_web_start.py:188` — `run_with_real_tmux`
- `scripts/tests/test_opencode_web_start.py:204` — per-test `TMUX_TMPDIR`
- `scripts/tests/test_opencode_web_start.py:216` — result poll
