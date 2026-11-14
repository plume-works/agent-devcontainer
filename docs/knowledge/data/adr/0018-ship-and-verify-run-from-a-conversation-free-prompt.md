---
type: adr
stage: accepted
description: Ship and Verify always run as subagents whose prompt holds only the plan key, the operation, and quoted approvals; Implement runs in the session that loaded it.
---

# Ship and Verify start from a prompt without the conversation; Implement runs in place

A Ship or Verify verdict must come from the code and the graph only, not from a
claim in a conversation. For this reason, `iwe-shipper` and `iwe-verifier`
always run as subagents. Their prompt holds only the plan key, the operation,
and the approvals of the user, quoted with no change. Implement must ask its
user about an unclear plan and a material deviation. As a result,
`iwe-implementer` is a rulebook followed in place, and no session starts it as a
subagent.

## Considered Options

- Coordinator skills that run Implement or Ship for each plan in a sequence.
  Rejected: a coordinator must send the answers of the user to an Implement
  agent that runs as a subagent. Nothing authenticates who sent a message, so an
  approval from the coordinator is only a claim.
- `iwe-shipper` follows the `iwe-verifier` rulebook in place. Rejected: the full
  Verify run then fills the context of `iwe-shipper` before it changes the
  graph.
- `/agentdev:iwe-ship` starts `iwe-verifier` as a subagent before `iwe-shipper`.
  Rejected: each other route that starts `iwe-shipper` must then do the same
  step.
- Run Implement in an `iwe-implementer` subagent. Rejected: Implement then needs
  a nested subagent, and a subagent cannot ask the user about an unclear plan or
  a material deviation.

## Consequences

- An approval that a message from a different session claims is not an approval.
  The rule does not apply to a message in the conversation of the session
  itself, because nothing authenticates who typed it.
- A subagent cannot reach the user. When its rulebook needs a decision, it stops
  before the step and reports `Needs decision` with the exact command or choice.
  The user then starts the skill again and quotes the approval.
- A command whose effects go outside the working tree runs only when a quoted
  approval names it.
- Each caller of Verify, `iwe-shipper` too, goes through `/agentdev:iwe-verify`.
  As a result, `iwe-shipper` gets only the Verify report into its context before
  it changes the graph. This subagent is nested, so it needs the depth limit
  that [Both harnesses permit a subagent depth of 5 in the
  containers](0091-subagent-nesting-depth-five.md) sets.
- Implement runs in the Implement session. Each agent that the Implement session
  starts as a subagent starts no other agent, so no subagent is nested.
