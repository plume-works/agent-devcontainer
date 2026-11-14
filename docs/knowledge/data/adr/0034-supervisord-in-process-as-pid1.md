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
