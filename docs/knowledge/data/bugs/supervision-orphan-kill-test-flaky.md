---
type: bug
description: test_recovery_kills_what_a_crashed_service_left_in_its_group failed intermittently because it treated a killed orphan that its adopting PID 1 had not yet reaped as alive, and its fake child held the exec wrapper's output, so supervisord's group stop rather than the controller's group kill did the killing.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-27T18:00:00Z
stage: done
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

Two defects in the test, none in the controller.

**The assertion races a reaper.** The fake service's child is orphaned when the
service crashes, and the kernel reparents it to the nearest subreaper or PID 1.
Nothing in the test's process tree is a subreaper, so inside an `agent-opencode`
container the orphan's parent becomes the container's own PID 1, whose
supervisord reaps adopted children on its next poll, a fraction of a second
later. The controller's `SIGKILL` has already ended the orphan by then, but
`os.kill(pid, 0)` succeeds on a zombie, so the check fails whenever it runs
before that reap. At the failing assertion `/proc/<pid>/stat` shows state `Z`
with parent PID 1, and the zombie disappears without further action.
`test_sigterm_stops_in_dependency_order_and_reaps_process_groups` makes the same
check after shutdown and carries the same race.

**The test did not reach the code it names.** The child inherited the `exec`
wrapper's stdout, and the wrapper waits up to five seconds for that pipe to
close (`Captured.wait`). The wrapper therefore outlived the crashed service, so
supervisord still saw the program running, and the controller's `stop` before
the restart signalled the whole group (`killasgroup`). The test passed with
`Controller.restart`'s `os.killpg` removed.

## Fix

The fake child sends its output to `/dev/null`, so the wrapper exits with the
service and only the controller's group kill can end the orphan: with that
`os.killpg` removed, the orphan test now fails. Both tests assert the child is
no longer running through the file's `running` helper, which counts a zombie as
gone, polling for up to five seconds because the kill is asynchronous. This
matches the bootstrap-kill test, which already waited that way.

## Key references

Verified anchor points (line numbers as of 2026-10-27):

- `scripts/tests/test_agent_runtime_supervision.py:51` — the fake service's
  `with-child` mode
- `scripts/tests/test_agent_runtime_supervision.py:695` —
  `test_recovery_kills_what_a_crashed_service_left_in_its_group`; `:703` — the
  wait for the orphan to stop running
- `scripts/tests/test_agent_runtime_supervision.py:638` —
  `test_sigterm_stops_in_dependency_order_and_reaps_process_groups`
- `scripts/tests/test_agent_runtime_supervision.py:827` — `running`
- `.devcontainer/scripts/runtime-supervisor.py:349` — `Controller.restart`'s
  `os.killpg`
- `.devcontainer/scripts/runtime-supervisor.py:227` — `Captured.wait` joining
  the output reader
