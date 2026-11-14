---
type: adr
stage: accepted
description: Ship runs Verify itself, and the user cannot cancel the stop that a CRITICAL result causes.
---

# A CRITICAL result always stops Ship

Ship runs Verify itself, so the check always runs, and a `CRITICAL` result stops
the Ship run. A user cannot cancel this stop, because the Ship run then records
a durable claim that Verify found false. A plan with a `CRITICAL` stays active
for a correction, gets a revision that removes the work, or Ship cancels it.

## Considered Options

- Let Ship close a plan that has a task that the user does not want. Rejected: a
  revision through `/agentdev:iwe-plan` revise mode removes the task. Removal is
  a material scope change, so revise mode asks the user, and the Verify check
  stays complete.
- Ship does its own copy of the Verify checks. Rejected: two copies of one
  rulebook become different.

## Consequences

- A cancellation does not run Verify, because it records that the work stopped,
  not a behaviour.
