---
type: adr
stage: accepted
description: PID 1 runs the root bootstrap and then the main function of supervisord in the same process, and the `controller` event listener owns order and recovery.
---

# supervisord runs in the PID 1 process, and the controller event listener owns the order

PID 1 runs `agentdev-runtime bootstrap`, with the opt-in firewall, and then the
`main()` function of supervisord in the same process. For this reason,
supervisord reaps every orphan, while PID 1 can still exit nonzero when the
`controller` event listener fails, which the `main()` of supervisord itself
never does. supervisord only starts, signals, and reaps programs. The
`controller` event listener owns the start order and the recovery.

## Considered Options

- A wrapper shell or an init shim as PID 1. Rejected: it takes PID 1 away from
  supervisord.

## Consequences

- The firewall runs first, so that its rule flush cannot erase the rules that
  `dockerd` installs later.
- supervisord stops the programs from the highest priority down. The
  `controller` event listener has the highest priority, so it stops first and
  does not see the shutdown as a failure.
- In the standalone runtime, `opencode serve` runs in the foreground as a
  supervisord program, not in tmux, because tmux hides a crash from the
  `controller` event listener and continues after a stop. The Coder agent start
  command, `agentdev-runtime coder start`, keeps its tmux session, so that
  OpenCode continues when the Coder agent starts again.
