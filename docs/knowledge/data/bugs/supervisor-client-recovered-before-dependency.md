---
type: bug
description: When D-Bus crashes, the standalone runtime controller can find keyring exited before it confirms the D-Bus failure, restart keyring on keyring's own budget against a dead bus, and latch the runtime failed.
sources:
- resource: .devcontainer/scripts/runtime-supervisor.py
- resource: scripts/tests/test_agent_runtime_supervision.py
- resource: .devcontainer/scripts/runtime-health.sh
- resource: https://github.com/plume-works/agent-devcontainer/pull/511
stage: done
severity: medium
---

# Bug: a client is recovered on its own budget before its dependency's failure is confirmed

## Symptom

`test_dependency_outage_recovers_clients_outside_their_budget` fails
intermittently in the devcontainer image job. The rest of
`test_agent_runtime_supervision.py` passes, and the test passes when run alone
on an idle machine. The failure ends with this event sequence, with no
`start dbus` after the crash:

```
'crash dbus', 'lost keyring', 'start keyring', 'lost keyring', 'stop opencode'
```

In a real container the same sequence would latch the runtime failed when D-Bus
crashes under load, instead of restarting D-Bus and then refreshing keyring.

## Reproduction

1. Copy `scripts/tests/test_agent_runtime_supervision.py` to `./.tmp/`, and
   point its `REPO_ROOT` at the repository root.

2. In the copy's `FAKE_HEALTH`, add `[[ $1 == dbus ]] && sleep 0.4` as the first
   command after the shebang. This slows only the D-Bus probe, widening the
   window in which it runs against a dying D-Bus.

3. Run the copy's test a few times:

   ``` bash
   uv run pytest .tmp/test_agent_runtime_supervision.py::test_dependency_outage_recovers_clients_outside_their_budget \
     -q -p no:cacheprovider
   ```

   Most runs fail with the event sequence above. The unmodified test passes in
   the same environment.

## Root cause

`Controller.check_once` walks the services in startup order and handles the
first failure it confirms. A service that is still running but fails its probe
is confirmed only after `AGENTDEV_PROBE_FAILURES` consecutive failures (default
2). Until then the walk skips it, and a service that has exited counts as failed
at once.

When D-Bus crashes, the controller can query D-Bus while supervisord still
reports it running. That first probe fails and the walk moves past D-Bus.
Keyring, which needs the bus, has already exited by then, so later in the same
pass keyring counts as failed, and `recover` calls `restart_until_ready` against
keyring's own budget. Nothing checks whether keyring's `after` dependencies are
healthy. The restarted keyring finds no bus and exits again. Once its budget is
spent, keyring raises `ComponentFailure`, and because keyring is core that
latches the runtime.

This bypasses the intended path in
[standalone-opencode-runtime](../archive/2.0.0/architecture/standalone-opencode-runtime.md):
D-Bus recovers first, then its `refresh` list restarts keyring outside keyring's
budget.

The race is intermittent because the controller is event-driven. Every
supervisord event wakes it early from its pause, so D-Bus's own exit event
usually starts the pass that finds D-Bus exited first. The race is lost only
when a pass is already running as D-Bus dies. The real probes widen that window:
the D-Bus probe is a `gdbus call` and the keyring probe runs
`runtime-keyring.sh check`, each with a five-second timeout, so a slow probe
under load is as plausible in production as in the test.

## Fix

Fixed by [Escalate a client failure to the dependency that caused
it](../plans/20261030-dbus-keyring-flaky-test.md). When `check_once` confirms a
failure, `Controller.failing_dependency` walks the failed service's `after`
dependencies transitively, and returns the first one in startup order that is
long-running, `ready`, and fails `healthy()` at that moment. If it finds one,
the controller recovers that dependency instead of the client. The dependency's
`refresh` list then restarts the client outside the client's budget. The
client's failure corroborates the dependency's failed probe, so the debounce
does not apply. The accepted cost: a dependency that was only slow to answer is
restarted, taking its clients with it. The rule is recorded under `## Recovery`
in
[standalone-opencode-runtime](../archive/2.0.0/architecture/standalone-opencode-runtime.md),
together with why deferring the client was rejected.

`test_a_client_failure_escalates_to_its_failing_dependency` reproduces the race
deterministically. A wedged fake D-Bus drops readiness but keeps running, and a
debounce too high to confirm it means only escalation can recover it.

Rejected directions:

- **Not charging the client's budget while its dependency is down.** It still
  restarts the client against a dead dependency, and it removes the budget's
  bound on those restarts.
- **Dependency-ordered recovery**
  ([dependency-ordered-recovery](../someday/dependency-ordered-recovery.md)). It
  covers this case, but it is the general init-system behavior that idea was
  held back to avoid, and this defect does not need it.

Still unknown: whether Xpra or OpenCode exit or only degrade when their
dependency is replaced. That decides whether the defect reached beyond keyring
in practice. The fix covers any client that exits.

## Key references

- `.devcontainer/scripts/runtime-supervisor.py::Controller.check_once` —
  `Controller.check_once`;
  `.devcontainer/scripts/runtime-supervisor.py::Controller.check_once` — an
  exited service counts as failed at once;
  `.devcontainer/scripts/runtime-supervisor.py::Controller.check_once` — the
  probe-failure debounce;
  `.devcontainer/scripts/runtime-supervisor.py::Controller.check_once` — the
  escalation to a failing dependency
- `.devcontainer/scripts/runtime-supervisor.py::Controller.failing_dependency` —
  `Controller.failing_dependency`
- `.devcontainer/scripts/runtime-supervisor.py::Controller.recover` —
  `Controller.recover`;
  `.devcontainer/scripts/runtime-supervisor.py::Controller.recover` — it skips a
  dependent in the `refresh` list
- `.devcontainer/scripts/runtime-supervisor.py::Controller.refresh_clients` —
  `Controller.refresh_clients`;
  `.devcontainer/scripts/runtime-supervisor.py::Controller.refresh_clients` — it
  restarts only a `ready` client
- `.devcontainer/scripts/runtime-supervisor.py::Controller.pause` —
  `Controller.pause`, woken early by a process-state event;
  `.devcontainer/scripts/runtime-supervisor.py::control` — `control`, which
  queues every event
- `.devcontainer/scripts/runtime-health.sh › "dbus)"` — the D-Bus probe;
  `.devcontainer/scripts/runtime-health.sh › "$script_dir/runtime-keyring.sh"` —
  the keyring probe
- `.devcontainer/scripts/runtime-supervisor.py::Controller.restart_until_ready`
  — `Controller.restart_until_ready`, which charges the service's own budget
- `.devcontainer/scripts/runtime-supervisor.py::DEPLOY_SERVICES` — `dbus`
  refreshes `keyring` and `xpra`;
  `.devcontainer/scripts/runtime-supervisor.py::DEPLOY_SERVICES` — `keyring` is
  core and runs `after` `dbus`
- `.devcontainer/scripts/runtime-supervisor.py::Settings` —
  `Settings.probe_failures` default
- `scripts/tests/test_agent_runtime_supervision.py::test_dependency_outage_recovers_clients_outside_their_budget`
  — `test_dependency_outage_recovers_clients_outside_their_budget`;
  `scripts/tests/test_agent_runtime_supervision.py::test_a_client_failure_escalates_to_its_failing_dependency`
  — `test_a_client_failure_escalates_to_its_failing_dependency`
- `scripts/tests/test_agent_runtime_supervision.py::FAKE_SERVICE` — the fake
  service's `wedge` trigger;
  `scripts/tests/test_agent_runtime_supervision.py::FAKE_SERVICE` — it exits
  once a service it needs loses readiness
- `scripts/tests/test_agent_runtime_supervision.py::FAKE_HEALTH` — `FAKE_HEALTH`
