---
type: adr
stage: accepted
---

# The workflow rulebooks are catalog agents

An explicit-only skill cannot carry a rulebook that another context needs:
Claude Code refuses it to the Skill tool in every context, subagents included,
and withholds it from an agent's `skills:` preload. So the rulebook has to sit
where a route without that gate reaches it, and the rulebooks of Plan,
Implement, Verify, and Ship are the agents `iwe-planner`, `iwe-implementer`,
`iwe-verifier`, and `iwe-shipper`. The Verify and Ship skills dispatch their
agent. The Plan and Implement skills have the user's session follow the agent
file in place, so that the session can ask the user. No skill holds the rules of
its workflow.

## Considered Options

- Preload the explicit-only skill into the agent through its `skills:` list.
  Rejected: Claude Code withholds an explicit-only skill from an agent's
  `skills:` preload, so the agent starts without its rulebook.
- Keep the rulebook in the explicit-only skill and have a subagent read its
  file. Rejected: the read succeeds, but the Skill tool's refusal tells the
  model not to replicate the workflow by other means. A model may rightly
  refuse, and one that complies has bypassed the gate.
- Keep the Verify rulebook in the skill behind a thin agent, as the
  `durable-knowledge-auditor` agent does with `durable-knowledge-audit`.
  Rejected: the skill would be both the rulebook and the entry point that must
  dispatch the agent, so a session that loads it already holds the rules it
  would otherwise run inline.
