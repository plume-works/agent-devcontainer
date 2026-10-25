---
type: task
created: 2026-10-25
stage: planned
priority: high
description: Run Verify from a fresh context on every entry point, by moving its rulebook into an iwe-verifier catalog agent that the verify skill dispatches and the Shipper follows in place.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-25T18:10:00Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-ship/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
---

# Run Verify from a fresh context

Ship already rests on the code and the graph alone: `/agentdev:iwe-ship`
dispatches `iwe-shipper` with only the plan key, the operation, and quoted
approvals. Verify does not. `/agentdev:iwe-verify` runs inline in whichever
context loads it, so a Verify run in the session that wrote the code judges that
code with the conversation's claims in view. This is the first of two plans; the
second, [Let Implement verify, fix, and revise on its
own](autonomous-implement-loop.md), dispatches the agent this one creates.

## What to do

- Move Verify's rulebook into a new `iwe-verifier` catalog agent, the way the
  Ship and Implement rulebooks live in `iwe-shipper` and `iwe-implementer`
  ([Explicit-only workflow
  agents](../architecture/explicit-only-workflow-agents.md)).
- `/agentdev:iwe-verify` dispatches `iwe-verifier` with only the plan key (or
  audit mode) and the user's approvals quoted verbatim, then re-posts its
  report. A verification command whose effects reach beyond the working tree
  comes back as `Needs decision`, as it does for the Shipper.
- `iwe-shipper` follows the `iwe-verifier` rulebook in place. It is already a
  fresh context, and keeping it a leaf avoids depending on nested dispatch,
  which OpenCode refuses at its default depth ([Nested subagent
  dispatch](../architecture/nested-subagent-dispatch.md)).
- On Codex, every dispatch that must start from a fresh context asks
  `spawn_agent` to forward no turns; the model otherwise forwards the whole
  conversation. That applies to the existing `iwe-shipper` dispatches too.
- Update the "Normal shipping requires a clean independent verification"
  requirement in [IWE workflow skills](../spec/iwe-workflow-skills.md) and the
  agent and dispatcher lists in the architecture doc.
