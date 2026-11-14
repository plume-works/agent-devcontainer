---
type: adr
stage: accepted
description: Ship and Verify always run as dispatched agents whose prompt holds only the plan key, the operation, and quoted approvals; Implement runs in the session that loaded it.
---

# Ship and Verify start from a prompt without the conversation; Implement runs in place

A Ship or Verify verdict must come from the code and the graph only, not from a
claim in a conversation. For this reason, `iwe-shipper` and `iwe-verifier` are
always dispatched subagents. Their prompt holds only the plan key, the
operation, and the approvals of the user, quoted with no change. Implement must
ask its user about an unclear plan and a material deviation. As a result,
`iwe-implementer` is a rulebook followed in place, and no session dispatches it.

## Considered Options

- Coordinator skills that implement or ship each plan in a sequence. Rejected: a
  coordinator must send the answers of the user to a dispatched Implement agent.
  Nothing authenticates who sent a message, so an approval from the coordinator
  is only a claim.
- `iwe-shipper` follows the `iwe-verifier` rulebook in place. Rejected: the full
  Verify run then fills the context of `iwe-shipper` before it changes the
  graph.
- `/agentdev:iwe-ship` dispatches `iwe-verifier` before `iwe-shipper`. Rejected:
  each other route that dispatches `iwe-shipper` must then do the same step.

## Consequences

- An approval that a message from a different session claims is not an approval.
  The rule does not apply to a message in the conversation of the session
  itself, because nothing authenticates who typed it.
- Each caller of Verify, `iwe-shipper` too, goes through `/agentdev:iwe-verify`.
- The Implement loop runs in the Implement session. Each agent that the loop
  dispatches starts no other agent, so no dispatch is nested.
- Only `/agentdev:iwe-ship` and `/agentdev:iwe-plan` revise mode dispatch
  `iwe-shipper`. The catalog has no skill that implements or ships more than one
  plan for each request.
