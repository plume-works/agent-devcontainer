---
type: bug
description: Under pytest-xdist, the supervised-Xpra ingress tests pick X display numbers from a pid hash in one host-global range, so two workers can choose the same display and one's start reclaims, and kills, the other's live X server.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-02T05:00:00Z
sources:
- resource: scripts/tests/test_agent_runtime_ingress.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/xpra.py
- resource: .github/workflows/ci.yml
---

# Bug: supervised-Xpra tests can pick the same X display under pytest-xdist

## Symptom

Not yet observed failing. CI runs `uv run pytest -n 8` in an image with xpra
installed, so the three tests that start a supervised Xpra on a display from
`:200 + (pid + port) % 500` run concurrently on different workers. When two pick
the same number, one test's Xpra loses its X server mid-test: a request, an
`xpra info` session, or the 90-second readiness wait fails.

## Reproduction

Run `scripts/tests/test_agent_runtime_ingress.py` under pytest-xdist so two of
`test_supervised_xpra_serves_its_client_but_sessions_need_the_password`,
`test_supervised_xpra_without_a_password_keeps_sessions_open`, and
`test_supervised_xpra_refuses_to_duplicate_a_live_session` land on different
workers at once and hash to the same display, roughly 1 in 500 per concurrent
pair. Forcing it deterministically means starting two supervised servers on one
display from separate scratch directories.

## Root cause

X displays are host-global — `/tmp/.X<N>-lock` and `/tmp/.X11-unix/X<N>` — but
each test gives Xpra its own `HOME` and `XDG_RUNTIME_DIR` (`xpra_env`), and the
display number comes from a hash, not from anything the worker owns. On start,
`agentdev_runtime xpra` asks `session_running`, which reads `xpra list` in that
private environment and so cannot see the other worker's session; it then calls
`reclaim_orphaned_display`, which finds the other worker's `Xvfb-for-Xpra-<N>`
through the shared lock file and sends it `SIGTERM`.

The reclaim is correct for the runtime, which owns one desktop per container;
the defect is the tests' display allocation. Unverified: if `xpra list` also
reads a socket directory shared across workers, the second start instead fails
cleanly with "already live" and kills nothing — still a failure, but
non-destructive.

`test_supervised_xpra_reclaims_the_display_after_a_crash` is not affected: it
alone uses `:700 + pid % 200`, and a worker's pid is constant.

## Fix

Not yet fixed. Allocate displays per xdist worker: derive a block of display
numbers from `worker_id` (`gw<k>`, or `master` without `-n`) and step a
per-worker counter through it per test, so workers are disjoint by construction
and a test does not reuse a display whose Xvfb may still hold its lock from the
previous teardown. The crash test keeps a display disjoint from the fixture's,
and every range stays clear of `:100`, the runtime's default display. The
runtime is unchanged.

Not covered: two concurrent pytest runs on one host both have a `gw0`; closing
that needs a run-unique offset from the xdist controller
(`pytest_configure_node`).

## Key references

Verified anchor points (line numbers as of 2026-11-02):

- `scripts/tests/test_agent_runtime_ingress.py:220` — `xpra_env`, per-test
  `HOME` and `XDG_RUNTIME_DIR`
- `scripts/tests/test_agent_runtime_ingress.py:234` — `supervised_xpra`
- `scripts/tests/test_agent_runtime_ingress.py:238` — pid-hashed display
- `scripts/tests/test_agent_runtime_ingress.py:250` — teardown
  `server.terminate()`
- `scripts/tests/test_agent_runtime_ingress.py:318` — crash test's separate
  display range
- `py_packages/agentdev_runtime/agentdev_runtime/xpra.py:66` — `session_running`
- `py_packages/agentdev_runtime/agentdev_runtime/xpra.py:103` —
  `reclaim_orphaned_display`
- `py_packages/agentdev_runtime/agentdev_runtime/xpra.py:123` — `SIGTERM` to the
  lock holder
- `py_packages/agentdev_runtime/agentdev_runtime/xpra.py:241` — start path:
  reclaim when no session is visible
- `scripts/e2e/iwe-workflows/conftest.py:45` — `fixture_repo`, existing
  per-worker state from `worker_id`
- `.github/workflows/ci.yml:357` — CI's `pytest -n 8`
