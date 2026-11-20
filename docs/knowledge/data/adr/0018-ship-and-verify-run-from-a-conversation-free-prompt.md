---
type: adr
stage: accepted
description: Ship and Verify always run as dispatched agents whose prompt holds only the plan key, the operation, and quoted approvals; Implement runs in the session that loaded it.
---

# Ship and Verify start from a prompt without the conversation; Implement runs in place

Ship and Verify verdicts must rest on the code and the graph, never on what a
conversation asserted. So `iwe-shipper` and `iwe-verifier` always run as
dispatched subagents, whose prompt carries only the plan key, the operation or
mode, and the user's approvals quoted verbatim. Implement must ask the user
about an ambiguous plan and a material deviation, so `iwe-implementer` is a
rulebook followed in place in the session that loaded it and is never
dispatched.

## Considered Options

- Coordinator skills that implement or ship every plan in turn. Rejected: a
  coordinator needs a dispatched Implement agent that stops at every decision
  and a route for relaying the user's answers to it, and a relayed approval is a
  claim that nothing authenticates.
- `iwe-shipper` follows the `iwe-verifier` rulebook in place. Rejected: it puts
  the whole Verify run in the context of `iwe-shipper` ahead of its graph
  changes.
- `/agentdev:iwe-ship` dispatches `iwe-verifier` before `iwe-shipper`. Rejected:
  every other route that dispatches `iwe-shipper`, such as Plan answering a Ship
  blocker report, would need the same step.
- Run Implement in a dispatched `iwe-implementer`. Rejected: Implement would
  then need nested dispatch, and a dispatched agent cannot ask the user about an
  ambiguous plan or a material deviation.

## Consequences

- Nothing authenticates a sender, so an approval that another session's message
  claims the user gave is not an approval. Nothing authenticates who typed a
  message in the session's own conversation either; this rule governs only
  approvals that another session's message claims.
- A dispatched agent cannot reach the user. When its rulebook needs a decision,
  it stops before the step and reports `Needs decision` with the exact command
  or choice. The user then re-runs the skill and quotes the approval.
- A command whose effects go outside the working tree runs only when a quoted
  approval names it.
- Every caller of Verify, `iwe-shipper` included, goes through
  `/agentdev:iwe-verify`, so only the Verify report enters the context of
  `iwe-shipper` ahead of its graph changes. This dispatch is nested, so it needs
  the depth limit that [Both harnesses permit a subagent depth of 5 in the
  containers](0091-subagent-nesting-depth-five.md) sets.
- Implement runs in the Implement session. Every agent that the Implement
  session dispatches starts no other agent, so no dispatch from it is nested.
