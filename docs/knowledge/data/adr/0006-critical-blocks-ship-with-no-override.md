---
type: adr
stage: accepted
---

# A CRITICAL result stops Ship with no override

A normal Ship run runs Verify itself, so verification is not a step a user can
forget, and a `CRITICAL` result refuses the ship mechanically. A user cannot
override it, because the ship would then record a durable claim known to be
false. A plan with a `CRITICAL` stays active for fixes, is revised through
`/agentdev:iwe-plan` revise mode to drop the offending work, or is cancelled; a
known-false durable claim is never shipped.

## Considered Options

- Soften the no-override rule so that a plan with a task the user declined can
  ship. Rejected: a revision through `/agentdev:iwe-plan` revise mode drops the
  task instead. Dropping a task is a material scope change, so revise mode asks
  the user, and the gate stays whole.
- Ship runs its own copy of the Verify checks. Rejected: two copies of one
  rulebook drift apart.

## Consequences

- Cancellation is exempt from Verify, because it records abandonment, not
  behaviour.
