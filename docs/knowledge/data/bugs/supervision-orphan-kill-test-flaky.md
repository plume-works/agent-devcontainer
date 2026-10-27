---
type: bug
description: test_recovery_kills_what_a_crashed_service_left_in_its_group fails intermittently when the supervision tests run as root inside an agent-opencode container, on main as well as on feature branches; the cause is not yet known.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-27T16:00:00Z
sources:
- resource: scripts/tests/test_agent_runtime_supervision.py
- resource: .devcontainer/scripts/runtime-supervisor.py
---

# Bug: Orphan-kill supervision test fails intermittently

## Symptom

`test_recovery_kills_what_a_crashed_service_left_in_its_group` fails with
`Failed: DID NOT RAISE ProcessLookupError`: after Xpra's fake service crashes
and is restarted, `os.kill(orphan, 0)` still finds the child the crashed service
left behind. The rest of `test_agent_runtime_supervision.py` passes in the same
run.

## Reproduction

1. Inside a running `agent-opencode` container, check out `main`.

2. Run the test as root, as CI runs `scripts/tests`:

   ``` bash
   sudo -n env PATH="$PATH" /uv/venvs/project/bin/python -m pytest \
     scripts/tests/test_agent_runtime_supervision.py -p no:cacheprovider \
     -k kills_what_a_crashed
   ```

3. Repeat it a few times: it fails in most runs and passes in the others.

## Root cause

Not yet determined; finding it is tracked by [Find why the orphan-kill
supervision test is flaky](../backlog/supervision-orphan-kill-test-cause.md).

The leading hypothesis, untested: `Controller.restart` does `SIGKILL` the
orphan's process group, but the orphan, reparented outside the test's
supervisord, stays a zombie until the container's PID 1 reaps it, and
`os.kill(pid, 0)` succeeds on a zombie. Checking the orphan's `/proc/<pid>/stat`
state at the assertion (`Z` versus a live state) would confirm or kill it.

## Fix

Unfixed.

## Key references

Verified anchor points (line numbers as of 2026-10-27):

- `scripts/tests/test_agent_runtime_supervision.py:692` —
  `test_recovery_kills_what_a_crashed_service_left_in_its_group`
- `scripts/tests/test_agent_runtime_supervision.py:700` — the
  `ProcessLookupError` assertion
- `.devcontainer/scripts/runtime-supervisor.py:341` — `Controller.restart`, the
  process-group kill
