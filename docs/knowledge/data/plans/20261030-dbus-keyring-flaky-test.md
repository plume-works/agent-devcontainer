---
type: plan
created: 2026-10-30
release:
- bugs/supervisor-client-recovered-before-dependency
description: Make the runtime controller recover the failing long-running dependency, not the client, when a client fails while a service it depends on fails a probe, so a D-Bus outage restarts D-Bus and refreshes keyring instead of latching the runtime on keyring's budget.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T01:34:47Z
sources:
- resource: docs/knowledge/data/bugs/supervisor-client-recovered-before-dependency.md
- resource: .devcontainer/scripts/runtime-supervisor.py
- resource: scripts/tests/test_agent_runtime_supervision.py
- resource: https://github.com/plume-works/agent-devcontainer/actions/runs/40952296384/job/123732954994?pr=533
---

# Escalate a client failure to the dependency that caused it

## Context

[Bug: a client is recovered on its own budget before its dependency's failure is
confirmed](../bugs/supervisor-client-recovered-before-dependency.md). When D-Bus
dies, `Controller.check_once` can find keyring exited while D-Bus's first failed
probe is still inside the `AGENTDEV_PROBE_FAILURES` debounce. Keyring is then
restarted on its own budget against a dead bus, exhausts it, and, being core,
latches the runtime.

## Approach

**Escalate.** When `check_once` confirms that a ready long-running service has
failed (it exited, or reached the probe-failure debounce), it first looks for a
cause among that service's `after` dependencies, walked transitively. A
dependency counts only if it is long-running (one-shots have no probe), enabled
in the profile, currently `ready`, and not healthy right now (`healthy()`: not
in a running state, or one failed probe). If one is found, the controller
recovers the root-most such dependency, the first in startup order, instead of
the client. The client's failure corroborates the dependency's failed probe, so
the debounce does not apply. The dependency's `refresh` list then restarts the
client outside the client's budget, through the existing `recover` path. With no
failing dependency, behavior is unchanged.

The accepted cost: a dependency that was only slow to answer at that moment is
restarted, taking its clients with it.

Rejected: **Defer** (skip the failed client while a dependency fails a single
probe, and let the next pass confirm the dependency). `refresh_clients` restarts
only a `ready` client and `recover` skips a dependent in the `refresh` list, so
the waiting client cannot be marked unready and reads `ready` while it is down,
for up to one interval. The bug document already rejects not charging the
client's budget and dependency-ordered recovery.

## Implementation Steps

### Task 1: A deterministic regression test for the dependency race

**Files:** Modify: `scripts/tests/test_agent_runtime_supervision.py`

- [x] Add a `wedge` trigger to `FAKE_SERVICE`: when `$state/$name.wedge` exists,
  the service removes the file and its `.ready` marker, appends `wedge <name>`
  to the events, and keeps running without readiness until it is stopped. A
  wedged D-Bus makes every client that needs it exit at once while D-Bus itself
  still runs.
  - **Evidence:** commit 3234a92 adds the trigger to `FAKE_SERVICE`; the new
    test's run records `wedge dbus` followed by `lost keyring`.
- [x] Add a test that starts the deploy profile with
  `AGENTDEV_RECOVERY_ATTEMPTS='1'`, keyring needing D-Bus, and
  `AGENTDEV_PROBE_FAILURES` high enough that the debounce cannot confirm D-Bus
  within the test's wait. It wedges D-Bus and asserts that D-Bus and keyring
  each start twice, the runtime returns to `ready`, and nothing is latched.
  - **Evidence:** commit 3234a92 adds
    `test_a_client_failure_escalates_to_its_failing_dependency` with
    `AGENTDEV_PROBE_FAILURES='1000'`.
- [x] Run the new test against the current controller and confirm it fails with
  keyring exhausting its budget (red).
  - **Evidence:**
    `uv run pytest scripts/tests/test_agent_runtime_supervision.py::test_a_client_failure_escalates_to_its_failing_dependency`
    at commit 3234a92 fails with `keyring exhausted 1 recovery attempts`.

### Task 2: Escalate a client failure to its failing dependency

**Files:** Modify: `.devcontainer/scripts/runtime-supervisor.py`

- [x] Add a `Controller` method that returns the root-most long-running
  dependency of a service, walked transitively through `after`, that is `ready`
  and not `healthy()`, or `None`.
  - **Evidence:** commit 99de61a adds `Controller.failing_dependency`.
- [x] In `check_once`, after a failure is confirmed and before `recover`, look
  up that dependency; when one is found, log that the client's failure is
  escalated to it and recover the dependency instead of the client.
  - **Evidence:** commit 99de61a calls `failing_dependency` in
    `Controller.check_once` and recovers the cause it returns.
- [x] Run the Task 1 test and
  `test_dependency_outage_recovers_clients_outside_their_budget` (green).
  - **Evidence:** at commit 99de61a,
    `uv run pytest scripts/tests/test_agent_runtime_supervision.py -k "escalates_to_its_failing_dependency or dependency_outage_recovers"`
    passes both tests on three consecutive runs.

### Task 3: Record the escalation rule

**Files:** Modify:
`docs/knowledge/data/architecture/standalone-opencode-runtime.md`

- [ ] Add a bullet to `## Recovery`: a client failure is charged to the
  root-most long-running dependency that fails a probe at that moment, which is
  recovered and refreshes the client outside the client's budget; the dependency
  check bypasses the probe-failure debounce, and a dependency that was only slow
  is restarted. Name the rejected Defer direction and why, and point at the bug
  document for the other two.

### Task 4: The full supervision suite passes in CI

- [ ] The devcontainer image jobs (amd64 and arm64) on the pull request pass
  `scripts/tests/test_agent_runtime_supervision.py`.

## Spec changes

None — no behavioral change. The fix brings the controller in line with the
existing requirement in
[standalone-opencode-runtime](../spec/standalone-opencode-runtime.md) that the
runtime "recover affected clients coherently".

## Verification

- `uv run pytest scripts/tests/test_agent_runtime_supervision.py` passes,
  including the new wedge test, which fails on the controller before Task 2.
- The bug's reproduction (the D-Bus probe slowed by 0.4s in a copy of the test)
  passes on repeated runs.
- `python-lint-check.sh` is clean for the changed files.
- The devcontainer image jobs pass on the pull request.

## Out of scope

- Dependency-ordered recovery as a general init-system behavior
  ([dependency-ordered-recovery](../someday/dependency-ordered-recovery.md)).
- Changing which clients each service's `refresh` list names, or how the real
  D-Bus and keyring probes in `runtime-health.sh` behave.
- Changing the probe-failure debounce for a service whose own probe fails with
  no failed client.

## Key references

Verified anchor points (line numbers as of 2026-10-30):

- `.devcontainer/scripts/runtime-supervisor.py:260` — `Service`; `:265` —
  `after`; `:268` — `refresh`
- `.devcontainer/scripts/runtime-supervisor.py:290` — deploy profile: `dbus`
  refreshes `keyring` and `xpra`; `:291` — `keyring` runs `after` `dbus`; `:307`
  — the devcontainer profile's equivalent
- `.devcontainer/scripts/runtime-supervisor.py:540` — `Controller.probe`; `:557`
  — `Controller.healthy`
- `.devcontainer/scripts/runtime-supervisor.py:620` —
  `Controller.restart_until_ready`, which charges the service's own budget
- `.devcontainer/scripts/runtime-supervisor.py:641` — `Controller.recover`;
  `:657` — `Controller.refresh_clients`, which restarts only a `ready` client
- `.devcontainer/scripts/runtime-supervisor.py:725` — `Controller.check_once`;
  `:731` — an exited service counts as failed at once; `:735` — the
  probe-failure debounce; `:748` — the `recover` call
- `scripts/tests/test_agent_runtime_supervision.py:41` — `FAKE_SERVICE`; `:55` —
  its `crash` trigger
- `scripts/tests/test_agent_runtime_supervision.py:631` —
  `test_dependency_outage_recovers_clients_outside_their_budget`
