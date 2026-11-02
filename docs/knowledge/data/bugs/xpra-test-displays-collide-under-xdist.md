---
type: bug
stage: done
severity: low
description: Under pytest-xdist, the supervised-Xpra ingress tests picked X display numbers from a pid hash in one host-global range, so two workers could choose the same display and the second start refused it as already live.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-02T06:00:00Z
sources:
- resource: scripts/tests/test_agent_runtime_ingress.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/xpra.py
- resource: .github/workflows/ci.yml
---

# Bug: supervised-Xpra tests can pick the same X display under pytest-xdist

## Symptom

CI runs `uv run pytest -n 8` in an image with xpra installed, so the three tests
that start a supervised Xpra on a display from `:200 + (pid + port) % 500` run
concurrently on different workers. When two pick the same number, the second
test's Xpra exits at once and its fixture fails after the 90-second readiness
wait.

## Reproduction

Start two supervised servers, `agentdev_runtime xpra --supervised`, on one
display from separate scratch directories, each with its own `HOME` and
`XDG_RUNTIME_DIR`. The second prints
`Error: an Xpra session is already live on :<N>; refusing to start a duplicate.`
and exits; the first keeps serving. Under xdist the collision needs two of
`test_supervised_xpra_serves_its_client_but_sessions_need_the_password`,
`test_supervised_xpra_without_a_password_keeps_sessions_open`, and
`test_supervised_xpra_refuses_to_duplicate_a_live_session` on different workers
at once, hashing to the same display — roughly 1 in 500 per concurrent pair.

## Root cause

X displays are host-global, and the display number came from a hash rather than
from anything the worker owns. `session_running` reads `xpra list`, which sees
sessions across the private `HOME` and `XDG_RUNTIME_DIR` the tests set, so the
second start finds the first worker's live session and refuses the display. The
refusal is correct for the runtime, which owns one desktop per container; the
defect was the tests' display allocation.

## Fix

Each xdist worker owns a block of 20 displays starting at
`:200 + 20 * <worker index>` (`PYTEST_XDIST_WORKER`, index 0 without `-n`):
`worker_display()` rotates through its first 10 per test, so a test never reuses
a display the previous teardown's Xvfb may still hold, and the crash test takes
the fixed slot after them. Workers are disjoint by construction, and every
display stays clear of `:100`, the runtime's default. The runtime is unchanged.

Not covered: two concurrent pytest runs on one host both have a `gw0`; closing
that needs a run-unique offset from the xdist controller
(`pytest_configure_node`).

## Key references

Verified anchor points (line numbers as of 2026-11-02):

- `scripts/tests/test_agent_runtime_ingress.py:34` — `DISPLAY_BASE`,
  `DISPLAY_BLOCK`, `ROTATING_SLOTS`
- `scripts/tests/test_agent_runtime_ingress.py:39` — `worker_display`
- `scripts/tests/test_agent_runtime_ingress.py:249` — `supervised_xpra`
- `scripts/tests/test_agent_runtime_ingress.py:253` — rotating display per test
- `scripts/tests/test_agent_runtime_ingress.py:333` — crash test's fixed slot
- `py_packages/agentdev_runtime/agentdev_runtime/xpra.py:66` — `session_running`
- `py_packages/agentdev_runtime/agentdev_runtime/xpra.py:235` — duplicate
  refusal
- `.github/workflows/ci.yml:357` — CI's `pytest -n 8`
