---
type: adr
stage: accepted
description: Ship runs Verify itself, and a CRITICAL result stops the ship with no override by the user.
---

# A CRITICAL result stops Ship with no override

Ship runs Verify itself, so the check always runs, and a `CRITICAL` result stops
the ship. A user cannot override it, because the ship then records a durable
claim that Verify found false. A plan with a `CRITICAL` stays active for a
correction, gets a revision that removes the work, or Ship cancels it.

## Considered Options

- Ship a plan with a task that the user does not want. Rejected: a revision
  through `/agentdev:iwe-plan` revise mode removes the task. Removal is a
  material scope change, so revise mode asks the user, and the gate stays
  complete.
- Cancel the plan because of one task that is not done. Rejected: a revision
  that removes the task is the correct size of change.
- Ship does its own copy of the Verify checks. Rejected: two copies of one
  rulebook become different.

## Consequences

- A cancellation does not run Verify, because it records that the work stopped,
  not a behaviour.
- The gate stops only the defects that Verify has a rule for.
