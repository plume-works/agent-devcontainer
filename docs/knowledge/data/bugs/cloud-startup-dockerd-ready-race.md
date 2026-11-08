---
type: bug
description: The cloud session startup script reported a failed Docker start when dockerd exited after it had already become ready, which made its stubbed-daemon tests fail at random in CI.
sources:
- resource: .claude/startup.py
- resource: scripts/tests/test_cloud_startup.py
stage: done
severity: low
---

# Bug: cloud startup reports a ready dockerd as failed when it exits

## Symptom

`start_docker` in `.claude/startup.py` raises
`StartupError: dockerd exited with 0` although the Docker daemon answers. In CI
the `Devcontainer image` jobs fail at random in
`scripts/tests/test_cloud_startup.py`, in
`test_stale_daemon_pidfile_is_removed_before_dockerd_starts` and
`test_dockerd_log_keeps_earlier_runs`.

## Reproduction

1. Stub a `dockerd` that marks the daemon ready and exits 0 at once, as
   `stub_dockerd` in `scripts/tests/test_cloud_startup.py` does.
2. Make the first readiness probe after the launch answer "not ready" only once
   that `dockerd` has exited.
3. Call `start_docker()`: it raises `dockerd exited with 0`.

## Root cause

The wait loop probes readiness, then checks whether `dockerd` exited, and treats
an exit as a failure. A `dockerd` that becomes ready and exits between the two
checks is reported as failed. The stub daemon exits immediately, so the window
opens on any slow probe.

## Fix

`start_docker` treats an exited `dockerd` as a failure only when the daemon
still does not answer, so a daemon that is ready when its exit is seen counts as
started. `test_dockerd_that_exits_once_ready_counts_as_started` forces the probe
order that used to fail.
