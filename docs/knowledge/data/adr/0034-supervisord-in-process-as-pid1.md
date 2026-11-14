---
type: adr
stage: accepted
description: PID 1 runs the root bootstrap and then the main function of supervisord in the same process, and a controller event listener owns order and recovery.
---

# supervisord runs in the PID 1 process, and a controller owns the order

PID 1 runs the root bootstrap, with the opt-in firewall, and then the `main()`
function of supervisord in the same process. For this reason, supervisord reaps
each orphan, and PID 1 can still exit nonzero when the controller fails.
supervisord itself never exits nonzero. supervisord only starts, signals, and
reaps programs. The `controller` event listener owns the start order and the
recovery.

## Considered Options

- A wrapper shell or an init shim as PID 1. Rejected: supervisord is then not
  PID 1.

## Consequences

- The firewall runs first, so that its rule flush cannot remove the rules that
  `dockerd` adds later.
- The controller answers the listener protocol on one thread and does its work
  on a different thread, so a long recovery does not stop event delivery.
- The root bootstrap runs before supervisord, so the runtime account exists
  before supervisord reads a program that names it.
- Each program has `autostart=false`, `startretries=0`, and `autorestart=false`.
  Only the controller starts or restarts a program.
- A thread in PID 1 watches the controller. When the controller stops outside a
  shutdown, the thread stops supervisord, and the container ends.
- The controller writes its log to stderr, because its stdout is for the
  listener protocol. The output of each program goes to the stdout of
  supervisord and to `docker logs`.
- supervisord stops the programs from the highest priority down. The controller
  has the highest priority, so it stops first and does not see the shutdown as a
  failure. `stopasgroup` and `killasgroup` stop the full process group of each
  program.
