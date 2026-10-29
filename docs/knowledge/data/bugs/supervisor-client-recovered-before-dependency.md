---
type: bug
description: When D-Bus crashes, the standalone runtime controller can find keyring exited before it confirms the D-Bus failure, restart keyring on keyring's own budget against a dead bus, and latch the runtime failed.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-29T18:55:07Z
sources:
- resource: .devcontainer/scripts/runtime-supervisor.py
- resource: scripts/tests/test_agent_runtime_supervision.py
- resource: .devcontainer/scripts/runtime-health.sh
- resource: https://github.com/plume-works/agent-devcontainer/pull/511
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
[standalone-opencode-runtime](../architecture/standalone-opencode-runtime.md):
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

Not fixed, and no direction is decided. Two directions keep the `refresh` path
as the recovery for a dependency outage:

- **Defer.** `check_once` skips a failed service while any of its long-running
  `after` dependencies fails a single probe, so the next pass confirms the
  dependency and its `refresh` list restarts the client. This keeps the
  probe-failure debounce, and costs one extra probe per client failure and up to
  one interval of latency.
- **Escalate.** A failed service whose long-running dependency fails a probe at
  that moment is treated as the dependency's failure, and the dependency is
  recovered in the same pass. The client's exit corroborates the dependency's
  failed probe, so the debounce does not apply. The cost: a dependency that was
  only slow to answer is restarted, taking its clients with it.

Deferring cannot mark the waiting client unready. `refresh_clients` restarts
only a client whose status is `ready`, and `recover` skips a dependent that is
in the recovered service's `refresh` list, so a client marked `blocked` or
`recovering` while it waits is never restarted. It therefore reads `ready` while
it is down, for up to one interval. Escalating has no such gap: recovering the
dependency sets it `recovering`, which makes the runtime `pending`.

Rejected directions:

- **Not charging the client's budget while its dependency is down.** It still
  restarts the client against a dead dependency, and it removes the budget's
  bound on those restarts.
- **Dependency-ordered recovery**
  ([dependency-ordered-recovery](../someday/dependency-ordered-recovery.md)). It
  covers this case, but it is the general init-system behavior that idea was
  held back to avoid, and this defect does not need it.

Open questions for the fix:

- Whether the dependency check walks transitively. OpenCode needs keyring, which
  needs D-Bus, so a non-transitive check could escalate an OpenCode failure to
  keyring while D-Bus is the cause. Only long-running dependencies count: a
  one-shot such as `prepare` has no probe.
- Which clients exit when their dependency does. A replaced session bus takes
  gnome-keyring down with it; whether Xpra or OpenCode exit or only degrade
  decides whether the defect reaches beyond keyring in practice.
- A deterministic regression test. The slowed probe above makes the race likely,
  not certain. A fake D-Bus that drops readiness and holds before it exits would
  fix the order.

The spec already requires the runtime to "recover affected clients coherently",
so the fix needs no spec change. The chosen rule belongs in the `## Recovery`
section of
[standalone-opencode-runtime](../architecture/standalone-opencode-runtime.md),
with the rejected directions.

## Key references

Verified anchor points (line numbers as of 2026-10-29):

- `.devcontainer/scripts/runtime-supervisor.py:649` — `Controller.check_once`;
  `:656` — an exited service counts as failed at once; `:659` — the
  probe-failure debounce
- `.devcontainer/scripts/runtime-supervisor.py:565` — `Controller.recover`;
  `:572` — it skips a dependent in the `refresh` list
- `.devcontainer/scripts/runtime-supervisor.py:581` —
  `Controller.refresh_clients`; `:584` — it restarts only a `ready` client
- `.devcontainer/scripts/runtime-supervisor.py:484` — `Controller.pause`, woken
  early by a process-state event; `:781` — `control`, which queues every event
- `.devcontainer/scripts/runtime-health.sh:38` — the D-Bus probe; `:42` — the
  keyring probe
- `.devcontainer/scripts/runtime-supervisor.py:544` —
  `Controller.restart_until_ready`, which charges the service's own budget
- `.devcontainer/scripts/runtime-supervisor.py:260` — `dbus` refreshes `keyring`
  and `xpra`; `:261` — `keyring` is core and runs `after` `dbus`
- `.devcontainer/scripts/runtime-supervisor.py:135` — `Settings.probe_failures`
  default
- `scripts/tests/test_agent_runtime_supervision.py:616` —
  `test_dependency_outage_recovers_clients_outside_their_budget`
- `scripts/tests/test_agent_runtime_supervision.py:63` — the fake service exits
  once a service it needs loses readiness
- `scripts/tests/test_agent_runtime_supervision.py:76` — `FAKE_HEALTH`
